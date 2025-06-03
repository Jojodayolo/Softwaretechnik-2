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

    def upload_file_for_assistant(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            uploaded_file = self.client.files.create(
                file=f,
                purpose="assistants"
            )
        print(f"Datei hochgeladen. file_id: {uploaded_file.id}")
        time.sleep(2)
        return uploaded_file.id

    def _create_assistant(self, file_id: str) -> str:
        assistant = self.client.beta.assistants.create(
            name="Test Generator Assistant",
            description=(
                "Analysiere alle Dateien gründlich. "
                "Identifiziere ALLE testbaren Features (z.B. Buttons, Links, Formulare, JS, Backend-Routen etc.). "
                "Schreibe für jedes Feature mindestens einen Playwright-Test. "
                "Wenn die Antwort zu lang wird, beende mit 'CONTINUE' und fahre auf Nachfrage fort."
            ),
            model=self.model,
            tools=[{"type": "code_interpreter"}],
            tool_resources={
                "code_interpreter": {
                    "file_ids": [file_id]
                }
            }
        )
        print(f"Assistant erstellt. assistant_id: {assistant.id}")
        return assistant.id

    def _extract_assistant_response(self, thread_id):
        # Holt die zuletzt gepostete Assistant-Antwort aus dem Thread
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                answer = ""
                for c in msg.content:
                    if hasattr(c, "text") and hasattr(c.text, "value"):
                        answer += c.text.value
                return answer.strip()
        return ""

    def _should_continue(self, answer):
        # Prüft, ob eine Fortsetzung erforderlich ist
        patterns = [
            r'continue\s*$',  # englisch
            r'fortsetzung\s*$',  # deutsch
            r'ich fahre fort',  # typisch deutsch
            r'ich mache weiter', 
            r'ich werde die analyse.*fortsetzen', 
            r'ende der analyse', 
            r'es sind keine weiteren features',  # Stop-Pattern
        ]
        answer_lower = answer.strip().lower()
        # "CONTINUE" oder andere Signale am Ende der Antwort?
        if any(re.search(p, answer_lower) for p in patterns):
            # Aber: Wenn das Stop-Pattern gefunden wird, dann abbrechen!
            if re.search(r'ende der analyse|es sind keine weiteren features', answer_lower):
                return False
            return True
        return False

    def ask_with_file(self, file_path: str) -> str:
        file_id = self.upload_file_for_assistant(file_path)
        assistant_id = self._create_assistant(file_id)

        prompt = ("""
        Die hochgeladene Datei enthält eine gescrapte Webanwendung mit verschiedenen Routen, HTML-Komponenten.

        1. Analysiere ALLE enthaltenen Features, die automatisiert getestet werden können (z. B. Formulare, Uploads, Downloads, Authentifizierung, Dropdowns, dynamische Inhalte, Editor, etc.).
        2. Erstelle für JEDES gefundene Feature einen ausführbaren Selenium-Test in PYTHON .
        3. Schreibe die Tests in einer einzigen Python-Datei im pytest-Format (`test_*.py`). Jede Testfunktion sollte selbsterklärend sein und einen sprechenden Namen haben.
        4. Verwende für jeden Test die passenden Selenium-Selektoren. Schreibe die Imports und, falls nötig, Setup/Teardown mit.
        5. Gib am Ende ausschließlich eine lauffähige Python-Datei mit allen Tests aus. 
        6. Falls notwendig, kommentiere kurz den Zweck jedes Tests im Code.
        7. Die URLS findest du immer am anfang jedes dateiabschnitts
        8. Baue zwischen den aktionen waits ein, damit die tests erfolgreich durchlaufen
        Antworte bitte NUR mit dem Python-Code für die Testdatei, **keinen Fließtext**.
        """
        )

        thread = self.client.beta.threads.create()
        all_answers = []

        # Initiale Message
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        while True:
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id
            )

            print("Warte auf die Antwort des Assistants...")
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Run fehlgeschlagen: {run_status.status}")
                time.sleep(2)

            answer = self._extract_assistant_response(thread.id)
            print("Antwort-Abschnitt empfangen.")
            all_answers.append(answer)

            if self._should_continue(answer):
                # Nächster Durchgang, der Prompt kann gern leicht variieren
                self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=(
                        "Bitte fahre fort und analysiere weitere Features sowie generiere zusätzliche Playwright-Tests, wie im ersten Prompt beschrieben. "
                        "Wenn erneut nötig, schreibe am Ende 'CONTINUE'."
                    )
                )
                time.sleep(2)
            else:
                break

        # Kombiniere alle Antworten, entferne mehrfaches "CONTINUE" am Ende
        combined = "\n\n".join([re.sub(r'(continue|fortsetzung)\s*$', '', a, flags=re.IGNORECASE).strip() for a in all_answers])
        return combined.strip()

# --- Beispiel-Aufruf ---
# connector = OpenAIAPIConnector(model="gpt-4o")
# result = connector.ask_with_file("repository.txt")
# print(result)
