import os
import time
from dotenv import load_dotenv
from openai import OpenAI

#gpt-4o-mini
class OpenAIAPIConnector:
    def __init__(self,  model: str):
        load_dotenv()  
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)


    def ask(self, prompt: str) -> str:        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
    
    def upload_file_for_assistant(self, file_path: str) -> str:
        """
        Lädt eine Datei für die Assistants-API hoch und gibt die file_id zurück.
        """
        with open(file_path, "rb") as f:
            uploaded_file = self.client.files.create(
                file=f,
                purpose="assistants"
            )
        print(f"Datei hochgeladen. file_id: {uploaded_file.id}")
        return uploaded_file.id

    def ask_with_file(self, prompt: str, file_path: str) -> str:
        """
        Stellt eine Frage unter Verwendung einer Datei über die Assistants-API.
        """
        file_id = self.upload_file_for_assistant(file_path)

        # 1. Assistant erstellen
        assistant = self.client.beta.assistants.create(
            name="File Assistant",
            instructions="Beantworte Fragen auf Basis der bereitgestellten Datei.",
            tools=[{"type": "code_interpreter"}],
            model=self.model
        )

        # 2. Thread erstellen
        thread = self.client.beta.threads.create()

        # 3. Message mit Datei senden
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
            file_ids=[file_id]
        )

        # 4. Run starten
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        # 5. Auf Antwort warten (Polling)
        while True:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run fehlgeschlagen: {run_status.status}")
            time.sleep(1)

        # 6. Antwort extrahieren
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        last_message = messages.data[0]
        return last_message.content[0].text.value