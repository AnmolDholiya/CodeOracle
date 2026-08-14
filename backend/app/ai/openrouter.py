import os
import json
import asyncio
from typing import Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

import openai
from openai import AsyncOpenAI

from app.ai.provider import AIProvider
from app.ai.schemas import AIResponse
from app.ai.prompts import SYSTEM_PROMPT_CODEORACLE
from app.ai.exceptions import (
    AIError,
    AIConfigurationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIInsufficientCreditsError,
    AIProviderError,
    AIValidationError
)

T = TypeVar("T", bound=BaseModel)

def get_configured_max_tokens() -> int:
    """Reads OPENROUTER_MAX_TOKENS env variable safely with fallback to 300."""
    val = os.getenv("OPENROUTER_MAX_TOKENS", "300").strip()
    try:
        num = int(val)
        return num if num > 0 else 300
    except ValueError:
        return 300

class OpenRouterProvider(AIProvider):
    """OpenRouter AI Provider implementation using AsyncOpenAI client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model = model or os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001").strip()
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()

        # Configuration check
        self.is_configured = bool(
            self.api_key and 
            self.api_key != "your_openrouter_api_key_here" and
            len(self.api_key) > 5
        )

        if self.is_configured:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/CodeOracle",
                    "X-Title": "CodeOracle AI Engine"
                }
            )
        else:
            self.client = None

    def _ensure_configured(self):
        if not self.is_configured or not self.client:
            raise AIConfigurationError(
                "OpenRouter API key is missing or not configured. "
                "Please set OPENROUTER_API_KEY in your .env file."
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.2,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0
    ) -> AIResponse:
        """Asynchronously sends a completion request to OpenRouter."""
        self._ensure_configured()
        effective_max_tokens = max_tokens if max_tokens is not None else get_configured_max_tokens()

        messages = []
        sys_prompt = system_prompt or SYSTEM_PROMPT_CODEORACLE
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async def _make_call():
                return await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature if temperature is not None else 0.2,
                    max_tokens=effective_max_tokens,
                )

            response = await asyncio.wait_for(_make_call(), timeout=timeout or 30.0)

            if not response or not response.choices or not response.choices[0].message:
                raise AIProviderError("OpenRouter returned an empty or invalid response.")

            content = response.choices[0].message.content or ""
            if not content.strip():
                raise AIProviderError("OpenRouter returned empty text output.")

            prompt_tokens = response.usage.prompt_tokens if response.usage else None
            completion_tokens = response.usage.completion_tokens if response.usage else None

            return AIResponse(
                text=content.strip(),
                model_used=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

        except asyncio.TimeoutError:
            raise AITimeoutError(f"AI request timed out after {timeout} seconds. Please try again.")
        except openai.AuthenticationError as auth_err:
            raise AIAuthenticationError(f"OpenRouter API key authentication failed: {str(auth_err)}")
        except openai.RateLimitError as rate_err:
            err_msg = str(rate_err).lower()
            if "402" in err_msg or "afford" in err_msg or "credit" in err_msg:
                raise AIInsufficientCreditsError("OpenRouter credit/token limit is too low for this request.")
            raise AIRateLimitError(f"OpenRouter API rate limit exceeded: {str(rate_err)}")
        except openai.APIStatusError as status_err:
            err_body = str(status_err.message or "").lower()
            if status_err.status_code == 402 or "afford" in err_body or "credit" in err_body:
                raise AIInsufficientCreditsError("OpenRouter credit/token limit is too low for this request.")
            elif status_err.status_code in (401, 403):
                raise AIAuthenticationError("OpenRouter API authentication failed (HTTP 401/403).")
            elif status_err.status_code == 429:
                raise AIRateLimitError("OpenRouter API rate limit exceeded (HTTP 429).")
            raise AIProviderError(f"OpenRouter API returned error (HTTP {status_err.status_code}): {status_err.message}")
        except openai.APIConnectionError:
            raise AIProviderError("Unable to connect to OpenRouter API service. Check network connectivity.")
        except AIError:
            raise
        except Exception as exc:
            err_str = str(exc).lower()
            if "402" in err_str or "afford" in err_str or "credit" in err_str:
                raise AIInsufficientCreditsError("OpenRouter credit/token limit is too low for this request.")
            raise AIProviderError(f"Unexpected error during AI generation: {str(exc)}")

    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.1,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0
    ) -> T:
        """Asynchronously requests structured JSON output and validates against Pydantic schema."""
        effective_max_tokens = max_tokens if max_tokens is not None else get_configured_max_tokens()

        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Return your output strictly as a valid JSON object matching the required schema. "
            "Do NOT include any markdown codeblocks (```json), commentary, or extra text."
        )

        try:
            response = await self.generate(
                prompt=json_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=effective_max_tokens,
                timeout=timeout
            )
        except AIInsufficientCreditsError:
            # Single fallback retry attempt with max_tokens = 200 if initial attempt was > 200
            if effective_max_tokens > 200:
                print(f"[AI Fallback] Insufficient credits for max_tokens={effective_max_tokens}. Retrying ONCE with max_tokens=200...")
                response = await self.generate(
                    prompt=json_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=200,
                    timeout=timeout
                )
            else:
                raise

        raw_text = response.text.strip()
        
        # Clean potential markdown wrapping (e.g. ```json ... ```)
        if "```" in raw_text:
            parts = raw_text.split("```")
            for part in parts:
                cleaned_part = part.strip()
                if cleaned_part.startswith("json"):
                    cleaned_part = cleaned_part[4:].strip()
                if cleaned_part.startswith("{") and cleaned_part.endswith("}"):
                    raw_text = cleaned_part
                    break

        # Extract first '{' to last '}' if extra text exists
        start_idx = raw_text.find("{")
        end_idx = raw_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            raw_text = raw_text[start_idx:end_idx + 1]

        try:
            data_dict = json.loads(raw_text)
            return schema_class.model_validate(data_dict)
        except json.JSONDecodeError as json_err:
            # Attempt auto-repair for truncated JSON strings
            repaired = raw_text.strip()
            if repaired.count('"') % 2 != 0:
                repaired += '"'
            if not repaired.endswith("}"):
                if repaired.endswith("[") or repaired.endswith(","):
                    repaired = repaired.rstrip(",[")
                repaired += "}"
            try:
                data_dict = json.loads(repaired)
                return schema_class.model_validate(data_dict)
            except Exception:
                pass
            raise AIValidationError(f"AI response is not valid JSON: {str(json_err)}")
        except ValidationError as pydantic_err:
            raise AIValidationError(f"AI response JSON failed schema validation: {str(pydantic_err)}")
