import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self, model_name='gemini-flash-latest'):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate_content(self, prompt, retries=5):
        import time
        import random
        from google.api_core import exceptions
        
        base_delay = 2
        
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except exceptions.ResourceExhausted as e:
                # 429 Rate Limit
                if attempt == retries - 1:
                    print("❌ Max retries reached for rate limiting.")
                    raise e
                    
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"⚠️ Rate limit hit. Retrying in {delay:.2f}s...")
                time.sleep(delay)
            except Exception as e:
                print(f"Error calling LLM: {e}")
                raise e
