from fastapi import FastAPI
from app.core.config import settings
from app.api.webhooks import router as webhooks_router

app = FastAPI(title="CodePilot Ops", version="0.1.0")
app.include_router(webhooks_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }
