class BackendError(Exception):
    """Base class for all backend related errors."""
    pass


class ExtractionError(BackendError):
    """Raised when PDF extraction fails."""
    pass


class RetrievalError(BackendError):
    """Raised when document retrieval fails."""
    pass


class GeminiError(BackendError):
    """Raised for issues interacting with the Gemini API."""
    pass


class ValidationError(BackendError):
    """Raised for invalid inputs to public functions."""
    pass
