import json

import pytest

import backend.document_store as ds
from backend.exceptions import ValidationError


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Point persistence at a temp file and start from an empty store."""
    monkeypatch.setattr(ds.Config, "STORE_PATH", str(tmp_path / "store.json"))
    ds.document_store.clear()
    yield tmp_path
    ds.document_store.clear()


def test_starting_store_is_empty():
    assert ds.get_documents() == []


def test_add_and_get_document(sample_document):
    ds.add_document(sample_document)
    docs = ds.get_documents()
    assert [d.doc_id for d in docs] == ["cpp"]
    assert docs[0] is sample_document


def test_add_invalid_document_raises():
    with pytest.raises(ValidationError):
        ds.add_document("not a document")


def test_add_document_persists_to_file(isolated_store):
    ds.add_document(_doc())
    payload = json.loads((isolated_store / "store.json").read_text(encoding="utf-8"))
    assert "d1" in payload
    assert payload["d1"]["title"] == "Doc"
    assert payload["d1"]["pages"][0]["text"] == "hello"
    assert payload["d1"]["pages"][0]["page_number"] == 1


def test_load_documents_restores_store(isolated_store, sample_document):
    ds.add_document(sample_document)

    # Simulate a fresh process: in-memory store is empty, only the file remains.
    ds.document_store.clear()

    ds.load_documents()
    docs = ds.get_documents()
    assert len(docs) == 1
    restored = docs[0]
    assert restored.doc_id == "cpp"
    assert restored.title == "C++ Primer"
    assert len(restored.pages) == 2
    assert restored.pages[0].page_number == 1


def test_clear_store_empties_and_persists(isolated_store, sample_document):
    ds.add_document(sample_document)
    ds.clear_store()
    assert ds.get_documents() == []
    payload = json.loads((isolated_store / "store.json").read_text(encoding="utf-8"))
    assert payload == {}


def test_load_documents_missing_file_is_noop(tmp_path):
    ds.load_documents()
    assert ds.get_documents() == []


def _doc():
    from backend.models import Document, PageMetadata

    return Document(
        doc_id="d1",
        title="Doc",
        pages=[PageMetadata(page_number=1, text="hello")],
    )