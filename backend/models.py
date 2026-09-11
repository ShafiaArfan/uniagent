from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class PageMetadata:
    """Metadata for a single page of a document."""
    page_number: int
    text: str
    # Additional metadata placeholders (e.g., headings, keywords) can be added later.

@dataclass
class Document:
    """A processed document.

    Attributes:
        doc_id: Unique identifier (e.g., filename or UUID).
        title: Human‑readable title (defaults to filename).
        pages: List of PageMetadata objects.
        source_path: Original file path.
    """
    doc_id: str
    title: str
    pages: List[PageMetadata] = field(default_factory=list)
    source_path: str = ""

    def get_text(self) -> str:
        """Concatenate all page texts into a single string."""
        return " ".join(page.text for page in self.pages)

# Response structures for the public API
@dataclass
class SourceInfo:
    document: str
    pages: List[int]

@dataclass
class AgentResponse:
    answer: str
    sources: List[SourceInfo]
    grounded: bool
    # Optional additional fields (e.g., confidence) can be added later.
