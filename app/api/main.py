from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="CodePilot Ops", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }