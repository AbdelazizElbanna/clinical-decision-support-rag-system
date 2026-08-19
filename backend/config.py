import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEYS = [os.getenv("GROQ_API_KEY", "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"), "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", "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", "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", "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", "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", "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", "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"]
CHROMA_DISEASES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vectorstores", "diseases_chroma"))
CHROMA_DRUGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vectorstores", "drugs_chroma"))
CITIES_JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "cities.json")
EMBEDDING_MODEL = "BAAI/bge-m3"

# Must match exactly what the team used when building ChromaDB
DISEASES_COLLECTION = "diseases"   # 166 chunks - full cleaned dataset
DRUGS_COLLECTION = "drugs"

# LLM Model on Groq
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

