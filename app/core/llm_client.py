from openai import OpenAI
from anthropic import Anthropic
from app.core.config import settings


class LLMClient:
    """Provider-agnostic chat client. Add new providers by extending _build_client() and chat()."""

    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        self._client = self._build_client()

    def _build_client(self):
        if self.provider == "anthropic":
            return Anthropic(api_key=settings.llm_api_key)
        return OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
        )

    def chat(self, system: str, user: str, max_tokens: int = 1024) -> str:
        if self.provider == "anthropic":
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text

        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content


llm_client = LLMClient()
