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
            "Die hochgeladene Datei enthält eine gescrapte Webanwendung.\n\n"
            "1. Analysiere ausschließlich die **aktuell angehängte Datei**.\n"
            "2. Ignoriere alle vorherigen Prompts, Kontexte oder Dateien.\n"
            "3. Verwende **ausschließlich** die `TEST_URL`, die ganz unten in dieser Datei im Format `TEST_URL=...` angegeben ist.\n"
            "4. Erstelle für **jedes erkannte Feature** ausführbare Selenium-Tests in Python im pytest-Format (`test_*.py`).\n"
            "5. Die Testfunktionen sollen sprechende Namen haben und vollständig ausführbar sein.\n"
            "6. Antworte bitte **nur** mit Python-Code – kein Fließtext.\n"
            "7. Schreibe ganz am Anfang des Codes eine Kommentarzeile mit der verwendeten URL, z. B. `# URL verwendet: https://...`"
            "8. Verbinde dich gegen eine bestehende chromedriver session auf dem remote debugging port 9222 und localhost. Folgendermaßen kannst du dich verbinden: # 1) Finde chromedriver im PATHchromedriver_path = shutil.which(\"chromedriver\")if not chromedriver_path:raise RuntimeError(\" chromedriver wurde nicht gefunden. Bitte \'brew install chromedriver\' o.Ä. ausführen.\")# 2) Konfiguriere ChromeOptions für den Debug-Portoptions = Options()options.add_experimental_option(\"debuggerAddress\", \"127.0.0.1:9222\")# 3) Starte den ChromeDriver-Service (er öffnet keine neue Chrome-Instanz)service = Service(executable_path=chromedriver_path)service.start()# 4) Verbinde Selenium remote mit dem laufenden Debug-Chromedriver = webdriver.Remote(command_executor=service.service_url,options=options)"
            "9. Füge nach jedem Test eine 5sek Wartezeit ein, damit der Webserver die Anfragen handeln kann"
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
