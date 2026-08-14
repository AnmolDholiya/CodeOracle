import os
from dotenv import load_dotenv

# Absolute paths
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_ENV_PATH = os.path.join(BACKEND_DIR, ".env")
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
ROOT_ENV_PATH = os.path.join(ROOT_DIR, ".env")

def load_backend_environment() -> str:
    """Explicitly loads backend/.env and root/.env using absolute paths with override=True.
    
    Can be called dynamically at runtime so any updates to .env take effect immediately
    without requiring a server restart.
    """
    loaded = []
    # 1. Load root .env if present
    if os.path.exists(ROOT_ENV_PATH):
        load_dotenv(dotenv_path=ROOT_ENV_PATH, override=True)
        loaded.append(ROOT_ENV_PATH)
        
    # 2. Load backend/.env (takes highest priority)
    if os.path.exists(BACKEND_ENV_PATH):
        load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=True)
        loaded.append(BACKEND_ENV_PATH)
        
    if loaded:
        return "; ".join(loaded)
    else:
        load_dotenv(override=True)
        return "fallback"

# Automatically load on import
ENV_FILE_LOADED = load_backend_environment()
