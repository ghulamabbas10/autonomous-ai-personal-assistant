import httpx
import pytest

from app.agents.providers.base import ChatMessage, GenerationRequest
from app.agents.providers.mock import MockLLMProvider
from app.agents.providers.ollama import OllamaProvider
from app.agents.runtime import SYSTEM_PROMPT, ConversationalAgent, InputLimitError
from app.core.config import Settings


async def test_mock_provider_supports_all_contract_operations() -> None:
    provider = MockLLMProvider()
    request = GenerationRequest(messages=[ChatMessage("user", "Help me focus")])
    result = await provider.generate(request)
    chunks = [chunk async for chunk in provider.stream(request)]
    structured = await provider.generate_structured(request, {"title": "Reply"})
    embeddings = await provider.embed(["one", "two"])

    assert "no external AI service" in result.content
    assert "".join(chunks) == result.content
    assert structured["provider"] == "mock"
    assert len(embeddings) == 2 and len(embeddings[0]) == 32


async def test_agent_bounds_context_and_input() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        llm_max_context_messages=2,
        llm_max_input_characters=100,
        _env_file=None,
    )
    agent = ConversationalAgent(MockLLMProvider(), settings)
    result = await agent.respond(
        [ChatMessage("user", "old"), ChatMessage("assistant", "older"), ChatMessage("user", "new")]
    )
    assert result.content.startswith("I received your request: “new”")
    assert "untrusted data" in SYSTEM_PROMPT

    with pytest.raises(InputLimitError):
        await agent.respond([ChatMessage("user", "x" * 101)])


async def test_ollama_adapter_parses_generation_and_embeddings() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/chat":
            return httpx.Response(
                200,
                json={
                    "model": "qwen2.5:3b",
                    "message": {"content": "A local answer"},
                    "prompt_eval_count": 12,
                    "eval_count": 4,
                },
            )
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    provider = OllamaProvider(
        base_url="http://ollama:11434",
        model="qwen2.5:3b",
        embedding_model="nomic-embed-text",
        timeout_seconds=10,
    )
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        base_url="http://ollama:11434", transport=httpx.MockTransport(handler)
    )
    result = await provider.generate(GenerationRequest(messages=[ChatMessage("user", "hello")]))
    embeddings = await provider.embed(["hello"])
    await provider.close()

    assert result.content == "A local answer"
    assert result.input_tokens == 12 and result.output_tokens == 4
    assert embeddings == [[0.1, 0.2]]
