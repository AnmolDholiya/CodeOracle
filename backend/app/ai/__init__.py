import os
from app.core.config import load_backend_environment

# Ensure backend/.env is explicitly loaded
load_backend_environment()

from app.ai.provider import AIProvider
from app.ai.openrouter import OpenRouterProvider
from app.ai.gemini import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.schemas import AIResponse, AITestRequest, AITestResponse, AIStatusResponse
from app.ai.exceptions import (
    AIError,
    AIConfigurationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIProviderError,
    AIValidationError
)

def get_ai_provider() -> AIProvider:
    """Factory function returning active AI Provider instance based on environment configuration."""
    provider_type = os.getenv("AI_PROVIDER", "").lower().strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    
    # 1. Prefer Groq if AI_PROVIDER is groq or GROQ_API_KEY is configured
    if provider_type == "groq" or (provider_type == "" and groq_key and len(groq_key) > 5 and groq_key != "your_actual_groq_key"):
        return GroqProvider()

    # 2. Gemini fallback if configured explicitly
    if provider_type == "gemini" or (provider_type == "" and gemini_key and len(gemini_key) > 5 and gemini_key != "your_gemini_api_key_here"):
        return GeminiProvider()
    
    # 3. Default to GroqProvider if configured or OpenRouterProvider
    if groq_key:
        return GroqProvider()
        
    return OpenRouterProvider()

__all__ = [
    "AIProvider",
    "OpenRouterProvider",
    "GeminiProvider",
    "GroqProvider",
    "get_ai_provider",
    "AIResponse",
    "AITestRequest",
    "AITestResponse",
    "AIStatusResponse",
    "AIError",
    "AIConfigurationError",
    "AIAuthenticationError",
    "AIRateLimitError",
    "AITimeoutError",
    "AIProviderError",
    "AIValidationError",
]
