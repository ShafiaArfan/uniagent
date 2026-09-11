import pytest

from backend.config import Config


def test_validate_requires_api_key(monkeypatch):
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError):
        Config.validate()


def test_validate_passes_with_api_key(monkeypatch):
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "test-key")
    Config.validate()


def test_defaults_are_sensible():
    assert Config.GEMINI_MODEL
    assert Config.RETRIEVAL_TOP_K > 0
    assert 0.0 <= Config.CONFIDENCE_THRESHOLD <= 1.0