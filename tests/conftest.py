import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models import Document, PageMetadata


@pytest.fixture
def make_pdf(tmp_path):
    """Return a helper that writes a PDF whose pages contain the given texts."""

    def _make(pages, name="sample") -> Path:
        from reportlab.pdfgen import canvas

        path = tmp_path / f"{name}.pdf"
        pdf = canvas.Canvas(str(path))
        for text in pages:
            pdf.drawString(72, 720, text)
            pdf.showPage()
        pdf.save()
        return path

    return _make


@pytest.fixture
def sample_document():
    """A simple :class:`Document` usable by store/retriever/agent tests."""
    return Document(
        doc_id="cpp",
        title="C++ Primer",
        pages=[
            PageMetadata(page_number=1, text="classes and inheritance in cpp"),
            PageMetadata(page_number=2, text="polymorphism and templates"),
        ],
    )


@pytest.fixture
def other_document():
    """A second document to test multi-document retrieval."""
    return Document(
        doc_id="math",
        title="Calculus Notes",
        pages=[PageMetadata(page_number=1, text="limits derivatives and integrals")],
    )