import os
from dotenv import load_dotenv
from openai import OpenAI


class DeepSeekAPIConnector:
    def __init__(self,  model: str):
        load_dotenv()  
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
        self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def ask_with_file(self, file_path: str) -> str:
        prompt = (
            "The attached file content contains a scraped web application, test requirements, test URL and an example test.\n\n"
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

        # Dateiinhalt lesen (z. B. HTML, JSON, etc.)
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Prompt + Dateiinhalt kombinieren
        full_prompt = f"{prompt}\n\n---\n\nFile content:\n```text\n{file_content}\n```"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ''' You are an experienced developer. Analyze the provided file, which includes a scraped website, 
                manual test cases, the TEST_URL, and an example test. From this, identify testable features and 
                generate Playwright tests compatible with pytest. Use only the TEST_URL given in the file.'''},
                {"role": "user", "content": full_prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
