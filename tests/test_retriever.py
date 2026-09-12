import pytest

import backend.document_store as ds
import backend.retriever as retriever
from backend.exceptions import RetrievalError


@pytest.fixture(autouse=True)
def clean_state(monkeypatch, tmp_path):
    """Reset retriever globals and the document store before each test."""
    monkeypatch.setattr(ds.Config, "STORE_PATH", str(tmp_path / "store.json"))
    ds.document_store.clear()
    retriever._vectorizer = None
    retriever._document_ids = []
    retriever._doc_matrix = None
    yield
    ds.document_store.clear()


def test_build_index_requires_documents():
    with pytest.raises(RetrievalError):
        retriever._build_index([])


def test_retrieve_returns_most_relevant_document(sample_document, other_document):
    ds.document_store[sample_document.doc_id] = sample_document
    ds.document_store[other_document.doc_id] = other_document

    results = retriever.retrieve("what is a C++ class and inheritance", top_k=2)

    assert len(results) == 2
    top_doc = results[0][0]
    assert top_doc.doc_id == "cpp"
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_respects_top_k(sample_document, other_document):
    ds.document_store[sample_document.doc_id] = sample_document
    ds.document_store[other_document.doc_id] = other_document

    results = retriever.retrieve("cpp classes", top_k=1)

    assert len(results) == 1
    assert results[0][0].doc_id == "cpp"


def test_retrieve_with_empty_store_raises():
    with pytest.raises(RetrievalError):
        retriever.retrieve("anything")


def test_retrieve_reuses_existing_index(sample_document, monkeypatch):
    ds.document_store[sample_document.doc_id] = sample_document
    first = retriever.retrieve("cpp", top_k=1)

    monkeypatch.setattr(
        retriever, "_build_index", lambda docs: pytest.fail("index rebuilt")
    )
    second = retriever.retrieve("cpp", top_k=1)

    assert first == second