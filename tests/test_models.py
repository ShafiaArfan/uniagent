from backend.models import AgentResponse, Document, PageMetadata, SourceInfo


def test_document_get_text_joins_pages():
    doc = Document(
        doc_id="d1",
        title="Doc",
        pages=[
            PageMetadata(page_number=1, text="hello"),
            PageMetadata(page_number=2, text="world"),
        ],
    )
    assert doc.get_text() == "hello world"


def test_document_defaults():
    doc = Document(doc_id="d1", title="Doc")
    assert doc.pages == []
    assert doc.source_path == ""


def test_source_info_fields():
    s = SourceInfo(document="Doc", pages=[1, 2])
    assert s.document == "Doc"
    assert s.pages == [1, 2]


def test_agent_response_fields():
    r = AgentResponse(answer="a", sources=[], grounded=True)
    assert (r.answer, r.sources, r.grounded) == ("a", [], True)