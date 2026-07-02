from openai import OpenAI
from anthropic import Anthropic
from app.core.config import settings
from app.core.observability import langfuse_client, is_tracing_enabled


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

    def chat(self, system: str, user: str, max_tokens: int = 1024, trace_name: str = "llm_chat") -> str:
        if is_tracing_enabled():
            generation = langfuse_client.generation(
                name=trace_name,
                model=self.model,
                input={"system": system, "user": user},
            )
            try:
                output = self._do_chat(system, user, max_tokens)
                generation.end(output=output)
                return output
            except Exception as e:
                generation.end(level="ERROR", status_message=str(e))
                raise
        else:
            return self._do_chat(system, user, max_tokens)

    def _do_chat(self, system: str, user: str, max_tokens: int) -> str:
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
