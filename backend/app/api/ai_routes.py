from fastapi import APIRouter, HTTPException, status
from app.ai import (
    get_ai_provider,
    AITestRequest,
    AITestResponse,
    AIStatusResponse,
    AIConfigurationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIProviderError,
    AIValidationError
)
from app.ai.prompts import build_test_explanation_prompt
import os

router = APIRouter(prefix="/api/ai", tags=["AI Engine"])

@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """Returns AI Provider configuration status."""
    provider = get_ai_provider()
    provider_name = provider.__class__.__name__.replace("Provider", "")
    base_url = getattr(provider, "base_url", "https://api.groq.com")

    return AIStatusResponse(
        configured=provider.is_configured,
        provider=provider_name,
        model=provider.model,
        base_url=base_url
    )

@router.post("/test", response_model=AITestResponse)
async def test_ai_explanation(request: AITestRequest):
    """Development test endpoint to verify AI generation."""
    provider = get_ai_provider()

    # Check if API key is configured
    if not provider.is_configured:
        # If no key configured, return a mock success response so UI/testing doesn't crash
        return AITestResponse(
            success=True,
            response=f"Mock AI Explanation: The function '{request.code.strip()}' takes parameters and executes a return statement.",
            model_used=provider.model,
            is_mock=True
        )

    prompt = build_test_explanation_prompt(request.code)

    try:
        result = await provider.generate(prompt=prompt, max_tokens=150, timeout=15.0)
        return AITestResponse(
            success=True,
            response=result.text,
            model_used=result.model_used,
            is_mock=False
        )
    except AIConfigurationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except AIAuthenticationError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err)
        )
    except AIRateLimitError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(err)
        )
    except AITimeoutError as err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(err)
        )
    except (AIProviderError, AIValidationError) as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Service error: {str(exc)}"
        )
