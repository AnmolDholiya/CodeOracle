import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel
from fastapi.testclient import TestClient

from app.main import app
from app.ai.openrouter import OpenRouterProvider
from app.ai.schemas import AIResponse
from app.ai.exceptions import (
    AIConfigurationError,
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
    AIProviderError,
    AIValidationError
)

client = TestClient(app)

class SampleStructuredOutput(BaseModel):
    summary: str
    complexity: str

@pytest.mark.asyncio
async def test_1_missing_api_key():
    """Test 1: Missing API key raises AIConfigurationError."""
    provider = OpenRouterProvider(api_key="")
    with pytest.raises(AIConfigurationError) as exc_info:
        await provider.generate("Test prompt")
    assert "OpenRouter API key is missing" in str(exc_info.value)
    print("[PASS] Test 1: Missing API key raises AIConfigurationError")

@pytest.mark.asyncio
async def test_2_valid_api_request():
    """Test 2: Valid API request returns structured AIResponse."""
    provider = OpenRouterProvider(api_key="sk-or-test-valid-key")
    
    mock_choice = MagicMock()
    mock_choice.message.content = "This code adds two numbers."
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 5
    mock_completion = MagicMock(choices=[mock_choice], usage=mock_usage)
    
    provider.client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    res = await provider.generate("Explain code")
    assert isinstance(res, AIResponse)
    assert res.text == "This code adds two numbers."
    assert res.prompt_tokens == 10
    print("[PASS] Test 2: Valid API request returns expected AIResponse")

@pytest.mark.asyncio
async def test_3_invalid_api_key():
    """Test 3: Invalid API key raises AIAuthenticationError."""
    provider = OpenRouterProvider(api_key="sk-or-invalid-key")
    
    import openai
    mock_response = MagicMock(status_code=401, headers={})
    auth_err = openai.AuthenticationError(
        message="Invalid API Key",
        response=mock_response,
        body={"error": {"message": "Invalid API key"}}
    )
    provider.client.chat.completions.create = AsyncMock(side_effect=auth_err)
    
    with pytest.raises(AIAuthenticationError) as exc_info:
        await provider.generate("Test prompt")
    assert "authentication failed" in str(exc_info.value).lower()
    print("[PASS] Test 3: Invalid API key raises AIAuthenticationError")

@pytest.mark.asyncio
async def test_4_timeout():
    """Test 4: Timeout raises AITimeoutError."""
    provider = OpenRouterProvider(api_key="sk-or-test-key")
    
    async def slow_call(*args, **kwargs):
        await asyncio.sleep(2.0)
        return MagicMock()
        
    provider.client.chat.completions.create = AsyncMock(side_effect=slow_call)
    
    with pytest.raises(AITimeoutError) as exc_info:
        await provider.generate("Test prompt", timeout=0.1)
    assert "timed out" in str(exc_info.value).lower()
    print("[PASS] Test 4: Timeout raises AITimeoutError")

@pytest.mark.asyncio
async def test_5_rate_limit():
    """Test 5: Rate limit raises AIRateLimitError."""
    provider = OpenRouterProvider(api_key="sk-or-test-key")
    
    import openai
    mock_response = MagicMock(status_code=429, headers={})
    rate_err = openai.RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body={"error": {"message": "Rate limit exceeded"}}
    )
    provider.client.chat.completions.create = AsyncMock(side_effect=rate_err)
    
    with pytest.raises(AIRateLimitError) as exc_info:
        await provider.generate("Test prompt")
    assert "rate limit" in str(exc_info.value).lower()
    print("[PASS] Test 5: Rate limit raises AIRateLimitError")

@pytest.mark.asyncio
async def test_6_empty_response():
    """Test 6: Empty response raises AIProviderError."""
    provider = OpenRouterProvider(api_key="sk-or-test-key")
    
    mock_choice = MagicMock()
    mock_choice.message.content = ""  # Empty text
    mock_completion = MagicMock(choices=[mock_choice], usage=None)
    provider.client.chat.completions.create = AsyncMock(return_value=mock_completion)
    
    with pytest.raises(AIProviderError) as exc_info:
        await provider.generate("Test prompt")
    assert "empty" in str(exc_info.value).lower()
    print("[PASS] Test 6: Empty response raises AIProviderError")

@pytest.mark.asyncio
async def test_7_malformed_structured_json():
    """Test 7: Malformed structured JSON raises AIValidationError."""
    provider = OpenRouterProvider(api_key="sk-or-test-key")
    
    # Mock returning invalid JSON (not matching schema)
    provider.generate = AsyncMock(return_value=AIResponse(
        text="Invalid non-json response text here",
        model_used="test-model"
    ))
    
    with pytest.raises(AIValidationError) as exc_info:
        await provider.generate_structured("Test prompt", SampleStructuredOutput)
    assert "not valid json" in str(exc_info.value).lower()
    print("[PASS] Test 7: Malformed structured JSON raises AIValidationError")

def test_8_api_endpoint_post_test():
    """Test 8: POST /api/ai/test endpoint returns valid JSON schema."""
    res = client.post("/api/ai/test", json={"code": "def multiply(x, y): return x * y"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert "response" in data
    assert "model_used" in data
    print("[PASS] Test 8: POST /api/ai/test endpoint returned valid JSON schema")

def run_all_tests():
    print("=== Running Phase 5 OpenRouter AI Provider Test Suite ===")
    asyncio.run(test_1_missing_api_key())
    asyncio.run(test_2_valid_api_request())
    asyncio.run(test_3_invalid_api_key())
    asyncio.run(test_4_timeout())
    asyncio.run(test_5_rate_limit())
    asyncio.run(test_6_empty_response())
    asyncio.run(test_7_malformed_structured_json())
    test_8_api_endpoint_post_test()
    print("\nALL 8 PHASE 5 AI PROVIDER TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_tests()
