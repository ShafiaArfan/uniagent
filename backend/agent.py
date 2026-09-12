import os
import logging
from typing import List, Tuple

from .config import Config
from .exceptions import GeminiError, ValidationError
from .models import AgentResponse, SourceInfo
from .retriever import retrieve

_logger = logging.getLogger(__name__)

def _initialize_gemini_client():
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise GeminiError("google-generativeai package not installed.") from e

    if not Config.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=Config.GEMINI_API_KEY)
    
    # Auto-fetch available text models to guarantee a working version
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    if not available_models:
        raise GeminiError("No text generation models available for this API key.")
        
    # Verify the requested model exists, otherwise fallback to the first active model
    target_model = Config.GEMINI_MODEL
    full_target = f"models/{target_model}"
    if target_model not in available_models and full_target not in available_models:
        target_model = available_models[0]
    
    model = genai.GenerativeModel(target_model)
    return model.generate_content

_gemini_generate = None

def _get_gemini_generate():
    global _gemini_generate
    if _gemini_generate is None:
        _gemini_generate = _initialize_gemini_client()
    return _gemini_generate

def _build_prompt(question: str, retrieved_docs: List[Tuple[object, float]]) -> str:
    system_prompt = os.getenv(
        "SYSTEM_PROMPT",
        "You are an AI assistant that answers questions based on the given context. Only use information from the provided documents. If the answer cannot be found, respond with \"Information not found.\"",
    )
    snippets = []
    for doc, _score in retrieved_docs:
        snippets.append(f"Document: {doc.title}\n{doc.get_text()[:2000]}\n---")
    context = "\n".join(snippets)
    return f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {question}"

def ask_agent(question: str, conversation_history: List[dict]) -> AgentResponse:
    if not question:
        raise ValidationError("Question must be a non-empty string.")

    retrieved = retrieve(question)
    if not retrieved:
        return AgentResponse(answer="Information not found.", sources=[], grounded=False)

    prompt = _build_prompt(question, retrieved)
    try:
        generate = _get_gemini_generate()
        response = generate(prompt)
        answer_text = response.text.strip()
    except Exception as e:
        raise GeminiError(f"Gemini API call failed: {e}")

    grounded = "information not found" not in answer_text.lower()
    sources = [SourceInfo(document=doc.title, pages=[p.page_number for p in doc.pages]) for doc, _score in retrieved]
    
    return AgentResponse(answer=answer_text, sources=sources, grounded=grounded)
