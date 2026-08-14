import sys
import os
import asyncio

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import load_backend_environment, BACKEND_ENV_PATH
from app.ai import get_ai_provider

# Load environment using exact same mechanism as FastAPI app
env_loaded_path = load_backend_environment()

async def run_minimal_gemini_test():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()

    key_loaded = bool(api_key and len(api_key) > 5 and api_key != "your_gemini_api_key_here")
    key_prefix = api_key[:3] if key_loaded else "N/A"
    key_length = len(api_key) if key_loaded else 0

    print("--- ENVIRONMENT REPORT ---")
    print(f"environment file being loaded: {BACKEND_ENV_PATH}")
    print(f"API key loaded: {str(key_loaded).lower()}")
    print(f"key prefix: {key_prefix}")
    print(f"key length: {key_length}")
    print(f"model: {model_name}")

    provider = get_ai_provider()
    
    try:
        res = await provider.generate(prompt="Reply with exactly: GEMINI_OK", max_tokens=250, timeout=15.0)
        print(f"Gemini test result: SUCCESS ({res.text})")
        return True
    except Exception as exc:
        print(f"Gemini test result: FAIL ({type(exc).__name__}: {str(exc)[:150]})")
        return False

if __name__ == "__main__":
    asyncio.run(run_minimal_gemini_test())