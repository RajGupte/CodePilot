from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM (chat/completion)
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"

    # Embeddings
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    # Database
    database_url: str = "postgresql+psycopg://codepilot:codepilot@localhost:5432/codepilot"

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""

    # Observability
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None


settings = Settings()