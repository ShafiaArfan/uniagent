import os
from pathlib import Path
from typing import Union

from pypdf import PdfReader

from .models import Document, PageMetadata
from .exceptions import ExtractionError


def process_document(file_path: Union[str, Path]) -> Document:
    """Extract text from a PDF and return a :class:`Document`.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Document: An object containing page‑level metadata.

    Raises:
        ExtractionError: If the file cannot be read or is not a valid PDF.
    """
    try:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise ExtractionError(f"File not found: {file_path}")
        if file_path.suffix.lower() != ".pdf":
            raise ExtractionError("process_document only supports PDF files.")

        reader = PdfReader(str(file_path))
        pages: list[PageMetadata] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                # Continue with empty text for this page but log the issue.
                text = ""
            pages.append(PageMetadata(page_number=i, text=text))

        doc = Document(
            doc_id=file_path.stem,
            title=file_path.stem,
            pages=pages,
            source_path=str(file_path),
        )
        return doc
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Failed to extract PDF: {e}")
