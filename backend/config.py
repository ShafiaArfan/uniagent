import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from this file)
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # Fallback to default environment variables
    pass

class Config:
    """Central configuration for the backend.

    Reads required settings from environment variables. Add defaults as needed.
    """

    # Gemini API key (required)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Gemini model name (default to a reasonable model)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # Optional: storage path for persisted document store (JSON file)
    STORE_PATH: str = os.getenv(
        "DOCUMENT_STORE_PATH",
        str(Path(__file__).resolve().parents[1] / "document_store.json"),
    )
    # Retrieval settings
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    # Guardrail thresholds (e.g., confidence score)
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

    @classmethod
    def validate(cls) -> None:
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
