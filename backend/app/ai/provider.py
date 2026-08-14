from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from app.ai.schemas import AIResponse

T = TypeVar("T", bound=BaseModel)

class AIProvider(ABC):
    """Abstract Base Class interface for AI Providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> AIResponse:
        """Generates text response from LLM asynchronously."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> T:
        """Generates structured output validated against a Pydantic schema model."""
        pass
