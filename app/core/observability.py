"""Langfuse tracing setup.

Wrapping tracing at the LLM client level (rather than scattering trace calls
through every agent) means every agent call gets traced automatically, with
zero changes needed to triage.py / review.py — a single point of instrumentation
covering the whole system.
"""

from langfuse import Langfuse
from app.core.config import settings

langfuse_client = None

if settings.langfuse_public_key and settings.langfuse_secret_key:
    langfuse_client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host or "https://cloud.langfuse.com",
    )


def is_tracing_enabled() -> bool:
    return langfuse_client is not None
