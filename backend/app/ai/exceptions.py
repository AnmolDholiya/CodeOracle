class AIError(Exception):
    """Base exception class for all AI service operations."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class AIConfigurationError(AIError):
    """Raised when AI provider configuration or API key is missing or invalid."""
    pass

class AIAuthenticationError(AIError):
    """Raised when API key authentication fails (HTTP 401/403)."""
    pass

class AIRateLimitError(AIError):
    """Raised when API quota or rate limit is exceeded (HTTP 429)."""
    pass

class AITimeoutError(AIError):
    """Raised when an AI request times out."""
    pass

class AIInsufficientCreditsError(AIError):
    """Raised when OpenRouter credit or affordable token limit is insufficient (HTTP 402)."""
    pass

class AIProviderError(AIError):
    """Raised when the AI provider returns a server error or an invalid/empty response."""
    pass

class AIValidationError(AIError):
    """Raised when AI output fails JSON parsing or Pydantic validation."""
    pass
