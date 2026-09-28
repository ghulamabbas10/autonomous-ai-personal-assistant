from app.agents.providers.base import LLMProvider
from app.agents.providers.mock import MockLLMProvider
from app.agents.providers.ollama import OllamaProvider
from app.core.config import Settings


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            base_url=str(settings.llm_base_url),
            model=settings.llm_model,
            embedding_model=settings.embedding_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return MockLLMProvider(settings.llm_model)
