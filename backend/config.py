import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
CHROMA_DISEASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vectorstores", "diseases_chroma"))
CHROMA_DRUGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vectorstores", "drugs_chroma"))
CITIES_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "cities.json")
EMBEDDING_MODEL = "BAAI/bge-m3"

# Must match exactly what the team used when building ChromaDB
DISEASES_COLLECTION = "diseases"   # 166 chunks - full cleaned dataset
DRUGS_COLLECTION = "drugs"

# LLM Model on Groq
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
