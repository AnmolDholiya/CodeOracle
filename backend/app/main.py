import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import load_backend_environment

# Explicitly load backend/.env
load_backend_environment()

from app.api.routes import router as projects_router
from app.api.ai_routes import router as ai_router
from app.api.explanation_routes import router as explanation_router
from app.api.testing_routes import router as testing_router
from app.api.refactoring_routes import router as refactoring_router
from app.api.breaking_change_routes import router as breaking_change_router

app = FastAPI(
    title="CodeOracle API",
    description="AI-Powered Legacy Codebase Explainer & Modernizer API",
    version="1.0.0"
)

# Configure CORS dynamically based on environment
frontend_url = os.getenv("FRONTEND_URL", "").strip()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://code-oracle-gamma.vercel.app",
]

if frontend_url:
    # Avoid duplicates but ensure the configured URL is always present
    if frontend_url not in origins:
        origins.append(frontend_url)
    if not frontend_url.startswith("http"):
        https_url = f"https://{frontend_url}"
        http_url = f"http://{frontend_url}"
        if https_url not in origins:
            origins.append(https_url)
        if http_url not in origins:
            origins.append(http_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if os.getenv("ENVIRONMENT") == "production" or frontend_url else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects_router)
app.include_router(ai_router)
app.include_router(explanation_router)
app.include_router(testing_router)
app.include_router(refactoring_router)
app.include_router(breaking_change_router)

START_TIME = time.time()

@app.get("/")
def read_root():
    return {
        "name": "CodeOracle API",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health")
def root_health_check():
    return {"status": "ok"}

@app.get("/api/health")
def health_check():
    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "ready": True,
        "service": "CodeOracle Backend Engine",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
