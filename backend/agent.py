import os
import logging
from typing import List, Tuple

from .config import Config
from .exceptions import GeminiError, ValidationError
from .models import AgentResponse, SourceInfo
from .retriever import retrieve

_logger = logging.getLogger(__name__)


def _initialize_gemini_client():
    """Initialize the Gemini client using the Google Generative AI library.

    Returns a callable that takes a string prompt and returns the model's raw response.
    Raises GeminiError if the library is missing or the API key is not set.
    """
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise GeminiError(
            "google-generativeai package not installed. Install it via 'pip install google-generativeai'."
        ) from e

    if not Config.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY is not set in the environment.")

    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(Config.GEMINI_MODEL)
    return model.generate_content

# Lazy initialization so import cost is low.
_gemini_generate = None


def _get_gemini_generate():
    global _gemini_generate
    if _gemini_generate is None:
        _gemini_generate = _initialize_gemini_client()
    return _gemini_generate


def _build_prompt(question: str, retrieved_docs: List[Tuple[object, float]]) -> str:
    """Construct the prompt sent to Gemini.

    Includes a system prompt (can be customized via env var) and the most relevant
    document snippets. Each snippet lists the document name and the page numbers.
    """
    system_prompt = os.getenv(
        "SYSTEM_PROMPT",
        "You are an AI assistant that answers questions based on the given context. Only use information from the provided documents. If the answer cannot be found, respond with \"Information not found.\"",
    )
    snippets = []
    for doc, _score in retrieved_docs:
        # For simplicity, include the full text of the document.
        # In a real system we would include only relevant pages.
        snippets.append(f"Document: {doc.title}\n{doc.get_text()[:2000]}\n---")
    context = "\n".join(snippets)
    prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {question}"
    return prompt


def ask_agent(question: str, conversation_history: List[dict]) -> AgentResponse:
    """Public API to answer a question using Gemini.

    Args:
        question: User question string.
        conversation_history: List of previous message dicts (e.g.,
            [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]).
            Currently unused but kept for future extensions.

    Returns:
        AgentResponse with answer, source tracking and grounded flag.
    """
    if not question:
        raise ValidationError("Question must be a non‑empty string.")

    # Retrieve relevant documents.
    retrieved = retrieve(question)
    if not retrieved:
        # No relevant docs – respond with not‑found guardrail.
        return AgentResponse(
            answer="Information not found.",
            sources=[],
            grounded=False,
        )

    prompt = _build_prompt(question, retrieved)
    try:
        generate = _get_gemini_generate()
        response = generate(prompt)
        # The library returns a GenerateContentResponse; we extract text.
        answer_text = response.text.strip()
    except Exception as e:
        raise GeminiError(f"Gemini API call failed: {e}")

    # Simple grounded check: if the answer contains the placeholder phrase, mark ungrounded.
    grounded = "information not found" not in answer_text.lower()

    # Build source info from retrieved docs (using top document only for brevity).
    sources = []
    for doc, _score in retrieved:
        # Here we assume the whole document is cited; page numbers could be refined.
        sources.append(SourceInfo(document=doc.title, pages=[p.page_number for p in doc.pages]))

    return AgentResponse(answer=answer_text, sources=sources, grounded=grounded)
