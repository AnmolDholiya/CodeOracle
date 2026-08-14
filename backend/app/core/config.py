import os
from dotenv import load_dotenv

# Absolute path to backend directory (d:\CodeOracle\backend)
# config.py is at: d:\CodeOracle\backend\app\core\config.py
# Going up 2 levels gives d:\CodeOracle\backend
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_ENV_PATH = os.path.join(BACKEND_DIR, ".env")

def load_backend_environment() -> str:
    """Explicitly loads backend/.env using absolute path with override=True."""
    if os.path.exists(BACKEND_ENV_PATH):
        load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=True)
        return BACKEND_ENV_PATH
    else:
        load_dotenv(override=True)
        return "fallback"

# Automatically load on import
ENV_FILE_LOADED = load_backend_environment()
