import os
import json
import asyncio
import time
from typing import Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from groq import Groq
from app.core.config import load_backend_environment
from app.ai.provider import AIProvider
from app.ai.schemas import AIResponse
from app.ai.prompts import SYSTEM_PROMPT_CODEORACLE
from app.ai.exceptions import (
    AIError,
    AIConfigurationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIProviderError,
    AIValidationError
)

T = TypeVar("T", bound=BaseModel)

FALLBACK_MODEL = "llama-3.1-8b-instant"

def get_groq_max_tokens() -> int:
    """Reads GROQ_MAX_OUTPUT_TOKENS or GEMINI_MAX_OUTPUT_TOKENS env variable with fallback to 250."""
    val = os.getenv("GROQ_MAX_OUTPUT_TOKENS", os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "250")).strip()
    try:
        num = int(val)
        return num if num > 0 else 250
    except ValueError:
        return 250

class GroqProvider(AIProvider):
    """Official Groq AI Provider implementation using official groq SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        # Refresh environment from .env file so runtime updates are detected immediately
        load_backend_environment()

        self.api_key = (
            api_key or 
            os.getenv("GROQ_API_KEY", "").strip()
        )
        self.model = (
            model or 
            os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        )

        self.is_configured = bool(
            self.api_key and 
            self.api_key not in ["your_actual_groq_key", "your_groq_api_key_here", "your_openrouter_api_key_here"] and 
            len(self.api_key) > 5
        )

        if self.is_configured:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception:
                self.client = None
        else:
            self.client = None

    def _ensure_configured(self):
        # Re-check environment in case user just added or changed the key in .env
        load_backend_environment()
        fresh_key = os.getenv("GROQ_API_KEY", "").strip()
        if fresh_key and fresh_key != self.api_key and len(fresh_key) > 5:
            self.api_key = fresh_key
            try:
                self.client = Groq(api_key=self.api_key)
                self.is_configured = True
            except Exception:
                pass

        if not self.is_configured or not self.client:
            raise AIConfigurationError(
                "Groq API key is missing or invalid. "
                "Please set GROQ_API_KEY in backend/.env."
            )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.2,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0
    ) -> AIResponse:
        """Generates text response using Groq ChatCompletions API asynchronously."""
        self._ensure_configured()
        effective_max_tokens = max_tokens if max_tokens is not None else get_groq_max_tokens()
        sys_prompt = system_prompt or SYSTEM_PROMPT_CODEORACLE

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]

        last_exc = None
        current_model = self.model

        for attempt in range(2):  # Max 2 attempts
            start_time = time.time()
            try:
                def _call():
                    return self.client.chat.completions.create(
                        model=current_model,
                        messages=messages,
                        temperature=temperature if temperature is not None else 0.2,
                        max_tokens=effective_max_tokens
                    )

                response = await asyncio.to_thread(_call)

                if not response or not response.choices:
                    raise AIProviderError("Groq API returned empty choices response.")

                content = response.choices[0].message.content or ""
                duration_ms = int((time.time() - start_time) * 1000)

                if not content.strip():
                    raise AIProviderError("Groq returned empty text response.")

                # Logging
                print(f"[Groq Request] type: text, model: {current_model}, cache_hit: false, duration: {duration_ms}ms")

                return AIResponse(
                    text=content.strip(),
                    model_used=current_model,
                    prompt_tokens=getattr(getattr(response, "usage", None), "prompt_tokens", None),
                    completion_tokens=getattr(getattr(response, "usage", None), "completion_tokens", None)
                )

            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "429" in err_str or "rate_limit_exceeded" in err_str.lower() or "quota" in err_str.lower() or "tpm" in err_str.lower():
                    if attempt == 0 and current_model != FALLBACK_MODEL:
                        print(f"[Groq Rate Limit] 429 detected on {current_model}. Falling back to high-capacity {FALLBACK_MODEL} (Attempt 2/2)...")
                        current_model = FALLBACK_MODEL
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        raise AIRateLimitError("Groq API rate limit reached. Please wait a few moments before trying again.")
                elif "401" in err_str or "invalid_api_key" in err_str.lower() or "authentication" in err_str.lower():
                    raise AIAuthenticationError("Groq API key authentication failed. Check your GROQ_API_KEY.")
                raise AIProviderError(f"Groq generation error: {err_str[:150]}")

        raise last_exc or AIProviderError("Groq request failed after 2 attempts.")

    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.1,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0
    ) -> T:
        """Generates structured output validated against Pydantic schema model via Groq API."""
        self._ensure_configured()
        effective_max_tokens = max_tokens if max_tokens is not None else get_groq_max_tokens()
        base_sys_prompt = system_prompt or SYSTEM_PROMPT_CODEORACLE

        # Inject Pydantic JSON schema format instructions into system prompt
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        json_sys_prompt = (
            f"{base_sys_prompt}\n\n"
            f"CRITICAL REQUIREMENT: You MUST respond ONLY with valid JSON strictly matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do NOT include markdown formatting wrappers or conversational commentary."
        )

        messages = [
            {"role": "system", "content": json_sys_prompt},
            {"role": "user", "content": prompt}
        ]

        current_model = self.model

        async def _single_attempt(req_messages: list, target_model: str) -> T:
            def _call():
                return self.client.chat.completions.create(
                    model=target_model,
                    messages=req_messages,
                    response_format={"type": "json_object"},
                    temperature=temperature if temperature is not None else 0.1,
                    max_tokens=effective_max_tokens
                )

            response = await asyncio.to_thread(_call)

            if not response or not response.choices:
                raise AIProviderError("Groq API returned null response.")

            raw_text = response.choices[0].message.content or ""
            cleaned_text = raw_text.strip()

            if not cleaned_text:
                raise AIValidationError("AI explanation could not be parsed.")

            # Defensive block stripping
            if "```" in cleaned_text:
                blocks = cleaned_text.split("```")
                for block in blocks:
                    sub = block.strip()
                    if sub.startswith("json"):
                        sub = sub[4:].strip()
                    if sub.startswith("{") and sub.endswith("}"):
                        cleaned_text = sub
                        break

            start_idx = cleaned_text.find("{")
            end_idx = cleaned_text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                cleaned_text = cleaned_text[start_idx:end_idx + 1]

            try:
                data_dict = json.loads(cleaned_text)
            except json.JSONDecodeError:
                raise AIValidationError("AI explanation could not be parsed.")

            try:
                return schema_class.model_validate(data_dict)
            except ValidationError as val_err:
                raise AIValidationError(f"Schema validation failed: {str(val_err)[:100]}")

        last_exc = None
        for attempt in range(2):  # Max 2 attempts
            start_time = time.time()
            try:
                result = await _single_attempt(messages, current_model)
                duration_ms = int((time.time() - start_time) * 1000)

                print(f"[Groq Request] type: structured ({schema_class.__name__}), model: {current_model}, cache_hit: false, duration: {duration_ms}ms")
                return result

            except AIValidationError as val_err:
                if attempt == 0:
                    retry_messages = messages + [
                        {"role": "assistant", "content": "Failed to output matching JSON."},
                        {"role": "user", "content": "Return ONLY valid JSON matching the exact schema."}
                    ]
                    try:
                        result = await _single_attempt(retry_messages, current_model)
                        duration_ms = int((time.time() - start_time) * 1000)
                        print(f"[Groq Request] type: structured ({schema_class.__name__}) (retry), model: {current_model}, cache_hit: false, duration: {duration_ms}ms")
                        return result
                    except Exception:
                        raise AIValidationError("AI explanation could not be parsed.")
                raise val_err

            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "429" in err_str or "rate_limit_exceeded" in err_str.lower() or "quota" in err_str.lower() or "tpm" in err_str.lower():
                    if attempt == 0 and current_model != FALLBACK_MODEL:
                        print(f"[Groq Rate Limit] 429 detected on {current_model}. Falling back to high-capacity {FALLBACK_MODEL} (Attempt 2/2)...")
                        current_model = FALLBACK_MODEL
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        raise AIRateLimitError("Groq API rate limit reached. Please wait a few moments before trying again.")
                elif "401" in err_str or "invalid_api_key" in err_str.lower() or "authentication" in err_str.lower():
                    raise AIAuthenticationError("Groq API key authentication failed. Check your GROQ_API_KEY.")
                raise AIProviderError(f"Groq structured generation error: {err_str[:150]}")

        raise last_exc or AIRateLimitError("Groq API rate limit reached. Please wait before trying again.")
