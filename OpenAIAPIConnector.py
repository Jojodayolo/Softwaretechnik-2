import os
import time
import re
from dotenv import load_dotenv
from openai import OpenAI

class OpenAIAPIConnector:
    TOOL_INCOMPATIBLE_MODELS = {"o3-mini", "o1", "o4-mini"}

    def __init__(self, model: str):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY nicht gefunden! .env überprüfen.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.uses_assistant = model not in self.TOOL_INCOMPATIBLE_MODELS
        if self.uses_assistant:
            self.assistant_id = self._load_or_create_assistant_id()
            self.attached_file_ids = self._load_attached_file_ids()

    def _load_or_create_assistant_id(self) -> str:
        path = "assistant_id.txt"
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()

        assistant = self.client.beta.assistants.create(
            name="Test Generator Assistant",
            description="You are an experienced developer. Analyze the provided file...",
            model=self.model,
            tools=[{"type": "code_interpreter"}]
        )
        with open("assistant_id.txt", "w") as f:
            f.write(assistant.id)
        return assistant.id

    def _load_attached_file_ids(self):
        path = "attached_file_ids.txt"
        if os.path.exists(path):
            with open(path, "r") as f:
                return set(line.strip() for line in f if line.strip())
        return set()

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
        if self.uses_assistant:
            file_id = self.upload_file_for_assistant(file_path)
            thread = self.client.beta.threads.create()

            self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                tool_resources={
                    "code_interpreter": {"file_ids": [file_id]}
                }
            )

            prompt = self._build_prompt()
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )

            all_answers = []
            while True:
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id
                )

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
                all_answers.append(answer)

                if self._should_continue(answer):
                    self.client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content="Bitte fahre fort. Wenn nötig, beende mit 'CONTINUE'."
                    )
                    time.sleep(2)
                else:
                    break

            return "\n\n".join([
                re.sub(r'(continue|fortsetzung)\s*$', '', a, flags=re.IGNORECASE).strip()
                for a in all_answers
            ])

        else:
            with open(file_path, "r", encoding="utf-8") as f:
                file_text = f.read()

            prompt = self._build_prompt() + "\n\nDateiinhalt:\n" + file_text
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()

    def _build_prompt(self) -> str:
        return (
            "The uploaded file contains a scraped web application, test requirements, test URL and an example test.\n\n"
            "1. Analyze only the currently attached file.\n"
            "2. Ignore all previous prompts, contexts, or files.\n"
            "3. Use only the TEST_URL specified in the file.\n"
            "4. For each test requirement write an executable test and use the test example as the template.\n"
            "5. Test functions must have descriptive names and be fully executable.\n"
            "6. Respond only with Python code – no explanatory text.\n"
            "7. At the very top of the code, include a comment line with the used URL, e.g., # URL used: https://...\n"
            "8. Add a 5-second wait after each test to allow the web server to handle requests.\n"
            "9. Make sure every test class name starts with Test that it can be processed from pytest \n"
        )

    def reset_state(self):
        for file in ["thread_id.txt", "assistant_id.txt", "attached_file_ids.txt"]:
            if os.path.exists(file):
                os.remove(file)
                print(f"🗑️ {file} gelöscht.")

    def generate_requirements_from_image(self, image_path: str) -> str:
        if not self.uses_assistant:
            raise NotImplementedError("Bildanalyse ist mit diesem Modell nicht verfügbar.")

        file_id = self.upload_file_for_assistant(image_path)
        thread = self.client.beta.threads.create()

        prompt = (
            "This is a screenshot of a web application interface.\n\n"
            "Analyze the image carefully and generate clear, structured test requirements based on the visible UI.\n"
            "Focus specifically on:\n"
            "1. Testable user interactions (e.g., buttons, inputs, navigation elements)\n"
            "2. Expected behavior for each element or user action\n"
            "3. UI components relevant for functional or usability testing\n\n"
            "Format your response as a numbered list of concise, natural-language test requirements.\n"
            "- Do NOT write any code\n"
            "- Avoid vague statements; be specific and practical\n"
            "- Use clear wording suitable for QA or test case design\n"
        )

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_file", "image_file": {"file_id": file_id}}
            ]
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

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
        return answer.strip()
