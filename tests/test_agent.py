import pytest

from backend import agent
from backend.exceptions import GeminiError, RetrievalError, ValidationError


class FakeGeminiResponse:
    """Mimics the google-genai GenerateContentResponse duck type used by the agent."""

    def __init__(self, text):
        self.text = text

    def __call__(self, prompt):
        return self


def test_build_prompt_includes_context_and_question(sample_document):
    prompt = agent._build_prompt("what is a class?", [(sample_document, 0.9)])

    assert "what is a class?" in prompt
    assert "C++ Primer" in prompt
    assert "classes and inheritance in cpp" in prompt


def test_build_prompt_uses_custom_system_prompt(sample_document, monkeypatch):
    monkeypatch.setenv("SYSTEM_PROMPT", "custom instructions")
    prompt = agent._build_prompt("q", [(sample_document, 0.9)])
    assert prompt.startswith("custom instructions")


def test_ask_agent_empty_question_raises(monkeypatch):
    with pytest.raises(ValidationError):
        agent.ask_agent("", conversation_history=[])


def test_ask_agent_without_documents_returns_guardrail(monkeypatch):
    monkeypatch.setattr(agent, "retrieve", lambda question: [])
    response = agent.ask_agent("anything", conversation_history=[])

    assert response.answer == "Information not found."
    assert response.sources == []
    assert response.grounded is False


def test_ask_agent_grounded_answer(monkeypatch, sample_document):
    monkeypatch.setattr(
        agent,
        "retrieve",
        lambda question: [(sample_document, 1.0)],
    )
    monkeypatch.setattr(
        agent,
        "_get_gemini_generate",
        lambda: FakeGeminiResponse("A class is a user-defined type."),
    )

    response = agent.ask_agent("what is a class?", conversation_history=[])

    assert response.answer == "A class is a user-defined type."
    assert response.grounded is True
    assert len(response.sources) == 1
    assert response.sources[0].document == "C++ Primer"
    assert response.sources[0].pages == [1, 2]


def test_ask_agent_not_found_answer_is_ungrounded(monkeypatch, sample_document):
    monkeypatch.setattr(agent, "retrieve", lambda question: [(sample_document, 1.0)])
    monkeypatch.setattr(
        agent,
        "_get_gemini_generate",
        lambda: FakeGeminiResponse("Information not found."),
    )

    response = agent.ask_agent("unknown topic", conversation_history=[])

    assert response.grounded is False


def test_ask_agent_propagates_gemini_api_failure(monkeypatch, sample_document):
    monkeypatch.setattr(agent, "retrieve", lambda question: [(sample_document, 1.0)])

    def failing_generate():
        raise RuntimeError("network down")

    monkeypatch.setattr(agent, "_get_gemini_generate", failing_generate)

    with pytest.raises(GeminiError):
        agent.ask_agent("question", conversation_history=[])


def test_initialize_client_requires_api_key(monkeypatch):
    monkeypatch.setattr(agent.Config, "GEMINI_API_KEY", "")
    with pytest.raises(GeminiError):
        agent._initialize_gemini_client()


def test_retrieval_errors_from_ask_agent_are_not_swallowed(monkeypatch):
    def bad_retrieve(question):
        raise RetrievalError("index missing")

    monkeypatch.setattr(agent, "retrieve", bad_retrieve)
    with pytest.raises(RetrievalError):
        agent.ask_agent("hi", conversation_history=[])