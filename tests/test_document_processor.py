import pytest

from backend.document_processor import process_document
from backend.exceptions import ExtractionError


def test_process_pdf_extracts_pages(make_pdf):
    path = make_pdf(["first page text", "second page text"])
    doc = process_document(path)

    assert doc.doc_id == "sample"
    assert doc.title == "sample"
    assert doc.source_path == str(path)
    assert len(doc.pages) == 2
    assert [p.page_number for p in doc.pages] == [1, 2]
    assert doc.pages[0].text.strip() == "first page text"
    assert doc.pages[1].text.strip() == "second page text"
    assert "first page text" in doc.get_text()


def test_process_missing_file_raises(tmp_path):
    with pytest.raises(ExtractionError):
        process_document(tmp_path / "missing.pdf")


def test_process_non_pdf_extension_raises(tmp_path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(ExtractionError):
        process_document(text_file)


def test_process_directory_raises(tmp_path):
    with pytest.raises(ExtractionError):
        process_document(tmp_path)