# backend/strathy_app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/web_client.json")
TOKEN_FILE = os.getenv("TOKEN_PATH", "token.json")
