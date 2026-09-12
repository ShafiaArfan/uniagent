import logging
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from .models import Document, PageMetadata
from .config import Config
from .exceptions import RetrievalError

_logger = logging.getLogger(__name__)

# Global retriever state – built lazily.
_vectorizer: TfidfVectorizer | None = None
_document_ids: List[str] = []
_doc_matrix: np.ndarray | None = None


def _build_index(documents: List[Document]) -> None:
    """Build a TF‑IDF index for the supplied documents.

    This function populates the module‑level ``_vectorizer``, ``_document_ids``
    and ``_doc_matrix`` variables.
    """
    global _vectorizer, _document_ids, _doc_matrix
    if not documents:
        raise RetrievalError("No documents available for indexing")

    # Concatenate all page texts for each document.
    corpus = [doc.get_text() for doc in documents]
    _document_ids = [doc.doc_id for doc in documents]
    _vectorizer = TfidfVectorizer(stop_words="english")
    _doc_matrix = _vectorizer.fit_transform(corpus)
    _logger.debug("TF‑IDF index built for %d documents", len(documents))


def _ensure_index() -> None:
    """Make sure the TF‑IDF index is built; if not, build it from the store.
    """
    global _vectorizer
    if _vectorizer is None:
        # Lazy import to avoid circular dependency.
        from .document_store import get_documents
        docs = get_documents()
        _build_index(docs)


def retrieve(query: str, top_k: int | None = None) -> List[Tuple[Document, float]]:
    """Return the most relevant documents for a query.

    Args:
        query: The user query string.
        top_k: Number of top results to return; defaults to ``Config.RETRIEVAL_TOP_K``.

    Returns:
        List of ``(Document, score)`` tuples ordered by descending relevance.
    """
    try:
        _ensure_index()
        if _vectorizer is None or _doc_matrix is None:
            raise RetrievalError("Retriever not initialized")
        top_k = top_k or Config.RETRIEVAL_TOP_K
        query_vec = _vectorizer.transform([query])
        # Compute cosine similarity.
        similarities = (query_vec @ _doc_matrix.T).toarray().flatten()
        # Get top indices.
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results: List[Tuple[Document, float]] = []
        from .document_store import document_store
        for idx in top_indices:
            doc_id = _document_ids[idx]
            doc = document_store.get(doc_id)
            if doc is None:
                continue
            results.append((doc, float(similarities[idx])))
        return results
    except Exception as e:
        raise RetrievalError(f"Failed to retrieve documents: {e}")
