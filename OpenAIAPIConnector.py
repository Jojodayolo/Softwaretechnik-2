import os
import time
import re
from dotenv import load_dotenv
from openai import OpenAI

class OpenAIAPIConnector:

    def __init__(self, model: str):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY nicht gefunden! .env überprüfen.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.assistant_id = self._load_or_create_assistant_id()
        self.attached_file_ids = self._load_attached_file_ids()

    def _load_or_create_assistant_id(self) -> str:
        path = "assistant_id.txt"
        if os.path.exists(path):
            with open(path, "r") as f:
                assistant_id = f.read().strip()
                print(f"Assistant wiederverwendet: {assistant_id}")
                return assistant_id

        assistant = self.client.beta.assistants.create(
            name="Test Generator Assistant",
            description=(
                "Analysiere eine einzelne Datei. Identifiziere testbare Features. "
                "Generiere pytest-kompatiblen Selenium-Code. Verwende NUR die TEST_URL aus der Datei."
            ),
            model=self.model,
            tools=[{"type": "code_interpreter"}]
        )
        with open(path, "w") as f:
            f.write(assistant.id)
        print(f"Neuer Assistant erstellt: {assistant.id}")
        return assistant.id

    def _load_attached_file_ids(self):
        path = "attached_file_ids.txt"
        if os.path.exists(path):
            with open(path, "r") as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_attached_file_id(self, file_id: str):
        with open("attached_file_ids.txt", "a") as f:
            f.write(file_id + "\n")

    def upload_file_for_assistant(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            uploaded_file = self.client.files.create(file=f, purpose="assistants")
        print(f"Datei hochgeladen: {file_path}, file_id: {uploaded_file.id}")
        time.sleep(2)
        return uploaded_file.id

    def _extract_assistant_response(self, thread_id):
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                return "".join(
                    c.text.value for c in msg.content
                    if hasattr(c, "text") and hasattr(c.text, "value")
                ).strip()
        return ""

    def _should_continue(self, answer):
        patterns = [
            r'continue\s*$',
            r'fortsetzung\s*$',
            r'ich fahre fort',
            r'ich mache weiter',
            r'ich werde die analyse.*fortsetzen',
            r'ende der analyse',
            r'es sind keine weiteren features',
        ]
        answer_lower = answer.strip().lower()
        if any(re.search(p, answer_lower) for p in patterns):
            if re.search(r'ende der analyse|es sind keine weiteren features', answer_lower):
                return False
            return True
        return False

    def ask_with_file(self, file_path: str) -> str:
        file_id = self.upload_file_for_assistant(file_path)

        # Neuen Thread für diese Anfrage erstellen
        thread = self.client.beta.threads.create()
        thread_id = thread.id

        # Assistant für diese Datei konfigurieren
        self.client.beta.assistants.update(
            assistant_id=self.assistant_id,
            tool_resources={
                "code_interpreter": {
                    "file_ids": [file_id]
                }
            }
        )

        prompt = (
            "The uploaded file contains a scraped web application, test requirements, test URL and an example test.\n\n"
            "1. Analyze only the currently attached file.\n"
            "2. Ignore all previous prompts, contexts, or files.\n"
            "3. Use only the TEST_URL specified in the file.\n"
            "4. For each test requirement write an executable test and use the test example as the template.\n"
            "5. Test functions must have descriptive names and be fully executable.\n"
            "6. Respond only with Python code – no explanatory text.\n"
            "7. At the very top of the code, include a comment line with the used URL, e.g., # URL used: https://...\n"
            "8. Add a 5-second wait after each test to allow the web server to handle requests.\n"
        )

        # Prompt an Thread senden
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=prompt
        )

        all_answers = []

        while True:
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )

            print("Warte auf die Antwort des Assistants...")
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Run fehlgeschlagen: {run_status.status}")
                time.sleep(2)

            answer = self._extract_assistant_response(thread_id)
            print("Antwort-Abschnitt empfangen.")
            all_answers.append(answer)

            if self._should_continue(answer):
                self.client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content="Bitte fahre fort. Wenn nötig, beende mit 'CONTINUE'."
                )
                time.sleep(2)
            else:
                break

        combined = "\n\n".join([
            re.sub(r'(continue|fortsetzung)\s*$', '', a, flags=re.IGNORECASE).strip()
            for a in all_answers
        ])
        return combined.strip()

    def reset_state(self):
        """Löscht gespeicherte Thread- und Assistant-Dateien."""
        for file in ["thread_id.txt", "assistant_id.txt", "attached_file_ids.txt"]:
            if os.path.exists(file):
                os.remove(file)
                print(f"🗑️ {file} gelöscht.")



    def generate_requirements_from_image(self, image_path: str) -> str:
            """Send an image file (e.g. UI screenshot) to the assistant and get textual test requirements."""
            # Upload image
            file_id = self.upload_file_for_assistant(image_path)

            # Create thread
            thread = self.client.beta.threads.create()
            thread_id = thread.id

            # No need to update tools since this doesn't use code interpreter (just a simple prompt)
            prompt = (
                "Dies ist ein Screenshot einer Webanwendung.\n\n"
                "Analysiere das Bild und formuliere verständliche, strukturierte Testanforderungen für die gezeigte Benutzeroberfläche. "
                "Fokus: Testbare Funktionen, erwartetes Verhalten, relevante UI-Elemente. "
                "Antwort bitte in nummerierten Listenpunkten. Kein Python-Code – nur natürlichsprachliche Anforderungen."
            )

            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=[
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_file",
                        "image_file": {
                            "file_id": file_id
                        }
                    }
                ]
            )

            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )

            print("Warte auf Testanforderungen aus dem Bild...")

            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Run fehlgeschlagen: {run_status.status}")
                time.sleep(2)

            answer = self._extract_assistant_response(thread_id)
            print("✅ Anforderungen empfangen.")
            return answer.strip()