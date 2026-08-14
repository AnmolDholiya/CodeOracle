import os
import json
import asyncio
import time
from typing import Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from google import genai
from google.genai import types

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

def get_gemini_max_tokens() -> int:
    """Reads GEMINI_MAX_OUTPUT_TOKENS env variable safely with fallback to 250."""
    val = os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "250").strip()
    try:
        num = int(val)
        return num if num > 0 else 250
    except ValueError:
        return 250

class GeminiProvider(AIProvider):
    """Google Gemini AI Provider implementation using official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = (
            api_key or 
            os.getenv("GEMINI_API_KEY", "").strip() or 
            os.getenv("GOOGLE_API_KEY", "").strip()
        )
        self.model = (
            model or 
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
        )

        self.is_configured = bool(
            self.api_key and 
            self.api_key not in ["your_gemini_api_key_here", "your_openrouter_api_key_here"] and 
            len(self.api_key) > 5
        )

        if self.is_configured:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None
        else:
            self.client = None

    def _ensure_configured(self):
        if not self.is_configured or not self.client:
            raise AIConfigurationError(
                "Gemini API key is missing or invalid. "
                "Please set GEMINI_API_KEY in backend/.env."
            )

    def _extract_text_from_response(self, response) -> str:
        """Safely extracts text output from Gemini response object."""
        if not response:
            return ""
        
        try:
            if hasattr(response, "text") and response.text:
                return response.text.strip()
        except Exception:
            pass

        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    parts = getattr(candidate.content, "parts", [])
                    extracted = []
                    for part in parts:
                        txt = getattr(part, "text", "")
                        if txt:
                            extracted.append(txt.strip())
                    if extracted:
                        return "\n".join(extracted).strip()
        except Exception:
            pass

        return ""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.2,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0
    ) -> AIResponse:
        """Sends text generation request using google-genai SDK with backoff."""
        self._ensure_configured()
        effective_max_tokens = max_tokens if max_tokens is not None else get_gemini_max_tokens()

        config_kwargs = {
            "temperature": temperature if temperature is not None else 0.2,
            "max_output_tokens": effective_max_tokens
        }

        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        config = types.GenerateContentConfig(**config_kwargs)

        last_exc = None
        for attempt in range(2):  # Max 2 attempts as required
            start_time = time.time()
            try:
                def _call():
                    return self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config
                    )

                response = await asyncio.to_thread(_call)

                if response is None:
                    raise AIProviderError("Gemini API returned null response.")

                output_text = self._extract_text_from_response(response)
                duration_ms = int((time.time() - start_time) * 1000)

                if not output_text or not output_text.strip():
                    raise AIProviderError("Gemini returned empty response text.")

                # Development Rate Limit Logging
                print(f"[Gemini Request] type: text, model: {self.model}, cache_hit: false, duration: {duration_ms}ms")

                return AIResponse(
                    text=output_text,
                    model_used=self.model,
                    prompt_tokens=None,
                    completion_tokens=None
                )

            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    if attempt == 0:
                        print(f"[Gemini Rate Limit] 429 detected. Backing off for 2.0s (Attempt {attempt + 1}/2)...")
                        await asyncio.sleep(2.0)
                        continue
                    else:
                        raise AIRateLimitError("Gemini API rate limit reached. Please wait before generating another explanation.")
                elif "INVALID_ARGUMENT" in err_str or "API_KEY_INVALID" in err_str or "400" in err_str:
                    raise AIAuthenticationError("Gemini API key authentication failed.")
                elif "402" in err_str:
                    raise AIInsufficientCreditsError("Gemini quota or credit limit reached.")
                raise AIProviderError(f"Gemini generation error: {err_str[:150]}")

        raise last_exc or AIProviderError("Gemini request failed after 2 attempts.")

    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.1,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0
    ) -> T:
        """Sends structured JSON generation request with backoff, defensive parsing & schema validation."""
        self._ensure_configured()
        effective_max_tokens = max_tokens if max_tokens is not None else get_gemini_max_tokens()
        sys_prompt = system_prompt or SYSTEM_PROMPT_CODEORACLE

        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=temperature if temperature is not None else 0.1,
            max_output_tokens=effective_max_tokens,
            response_mime_type="application/json",
            response_schema=schema_class
        )

        async def _single_attempt(req_prompt: str) -> T:
            def _call():
                return self.client.models.generate_content(
                    model=self.model,
                    contents=req_prompt,
                    config=config
                )

            response = await asyncio.to_thread(_call)

            if response is None:
                raise AIProviderError("Gemini API returned null response.")

            raw_text = self._extract_text_from_response(response)

            if not raw_text or not raw_text.strip():
                raise AIProviderError("Gemini returned empty response for structured request.")

            cleaned_text = raw_text.strip()

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

            if not cleaned_text or cleaned_text.strip() == "":
                raise AIValidationError("Gemini returned empty structured JSON text.")

            try:
                data_dict = json.loads(cleaned_text)
            except json.JSONDecodeError:
                raise AIValidationError("Gemini returned an invalid structured response.")

            try:
                return schema_class.model_validate(data_dict)
            except ValidationError:
                raise AIValidationError("Gemini returned data that did not match the expected explanation format.")

        last_exc = None
        for attempt in range(2):  # Max 2 attempts
            start_time = time.time()
            try:
                result = await _single_attempt(prompt)
                duration_ms = int((time.time() - start_time) * 1000)

                print(f"[Gemini Request] type: structured ({schema_class.__name__}), model: {self.model}, cache_hit: false, duration: {duration_ms}ms")
                return result

            except AIValidationError as val_err:
                if attempt == 0:
                    retry_prompt = f"{prompt}\n\nIMPORTANT RETRY: Return ONLY valid JSON matching the exact schema."
                    try:
                        result = await _single_attempt(retry_prompt)
                        duration_ms = int((time.time() - start_time) * 1000)
                        print(f"[Gemini Request] type: structured ({schema_class.__name__}) (retry), model: {self.model}, cache_hit: false, duration: {duration_ms}ms")
                        return result
                    except Exception:
                        raise AIValidationError("Gemini returned data that did not match the expected explanation format.")
                raise val_err

            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    if attempt == 0:
                        print(f"[Gemini Rate Limit] 429 detected. Backing off for 2.0s (Attempt {attempt + 1}/2)...")
                        await asyncio.sleep(2.0)
                        continue
                    else:
                        raise AIRateLimitError("Gemini API rate limit reached. Please wait before generating another explanation.")
                elif "INVALID_ARGUMENT" in err_str or "API_KEY_INVALID" in err_str or "400" in err_str:
                    raise AIAuthenticationError("Gemini API key authentication failed.")
                elif "402" in err_str:
                    raise AIInsufficientCreditsError("Gemini quota or credit limit reached.")
                raise AIProviderError(f"Gemini structured generation error: {err_str[:150]}")

        raise last_exc or AIRateLimitError("Gemini API rate limit reached. Please wait before generating another explanation.")
