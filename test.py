import sys
import os
from dotenv import load_dotenv

load_dotenv()
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
print("TELEGRAM_BOT_TOKEN:", os.getenv("TELEGRAM_BOT_TOKEN"))
print("ALLOWED_USERS:", os.getenv("ALLOWED_USERS"))
print("ENVIRONMENT:", os.getenv("ENVIRONMENT"))