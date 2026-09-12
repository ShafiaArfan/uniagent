import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

class Config:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    STORE_PATH: str = os.getenv(
        "DOCUMENT_STORE_PATH",
        str(Path(__file__).resolve().parents[1] / "document_store.json"),
    )
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

    @classmethod
    def validate(cls) -> None:
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
