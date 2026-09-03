import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
PROJECT_OUTPUT_DIR = os.getenv("PROJECT_OUTPUT_DIR", "./generated_project")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your "
        "Gemini API key (https://aistudio.google.com/apikey)."
    )
