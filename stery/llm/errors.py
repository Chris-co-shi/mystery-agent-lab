class LLMError(Exception):
    """Base class for exceptions in this module."""

class LLMConfigError(LLMError):
    """Raised when LLM configuration is invalid"""

class LLMProviderError(LLMError):
    """Raised when provider return as unexpected error """

class LLMTimeoutError(LLMError):
    """Raised when provider timeout """

class LLMRateLimitError(LLMError):
    """Raised when provider rate limit """

class LLMAuthenticationError(LLMError):
    """Raised when provider authentication failed """

class LLMResponseError(LLMError):
    """Raised when provider response is invalid """
