import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY", "")

groq_client = Groq(api_key=api_key) if api_key else None