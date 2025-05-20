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


    def ask(self, prompt: str) -> str:        
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content