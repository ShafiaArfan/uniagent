import json
from pathlib import Path
from typing import List, Dict

from .models import Document
from .exceptions import ValidationError
from .config import Config

# Simple in‑memory store; persisted to a JSON file on demand.
document_store: Dict[str, Document] = {}


def _persist_store() -> None:
    """Write the current store to Config.STORE_PATH as JSON.

    This is a lightweight persistence mechanism for the prototype.
    """
    try:
        path = Path(Config.STORE_PATH)
        # Convert Document objects to serializable dicts.
        serialisable = {
            doc_id: {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "source_path": doc.source_path,
                "pages": [
                    {"page_number": p.page_number, "text": p.text}
                    for p in doc.pages
                ],
            }
            for doc_id, doc in document_store.items()
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(serialisable, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ValidationError(f"Failed to persist document store: {e}")


def _load_from_path(path_str: str) -> None:
    """Load documents from a JSON file into the in‑memory store."""
    path = Path(path_str)
    if not path.is_file():
        return  # Nothing to load.
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for doc_id, doc_data in data.items():
            pages = [
                # Recreate PageMetadata objects
                __import__("backend.models", fromlist=["PageMetadata"]).PageMetadata(
                    page_number=p["page_number"], text=p["text"]
                )
                for p in doc_data.get("pages", [])
            ]
            document = Document(
                doc_id=doc_data.get("doc_id", doc_id),
                title=doc_data.get("title", doc_id),
                pages=pages,
                source_path=doc_data.get("source_path", ""),
            )
            document_store[doc_id] = document
    except Exception as e:
        raise ValidationError(f"Failed to load document store: {e}")


def load_documents() -> None:
    """Public API to load persisted documents into memory.

    Should be called once at application start‑up.
    """
    _load_from_path(Config.STORE_PATH)


def get_documents() -> List[Document]:
    """Return a list of all stored :class:`Document` objects."""
    return list(document_store.values())


def add_document(document: Document) -> None:
    """Add a new document to the store and persist the change.

    Args:
        document: The :class:`Document` instance to store.
    """
    if not isinstance(document, Document):
        raise ValidationError("add_document expects a Document instance")
    document_store[document.doc_id] = document
    _persist_store()


def clear_store() -> None:
    """Utility to remove all documents (useful for tests)."""
    document_store.clear()
    _persist_store()
