import os
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