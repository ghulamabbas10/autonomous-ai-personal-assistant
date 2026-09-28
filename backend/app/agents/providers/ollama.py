import json
from collections.abc import AsyncIterator, Sequence
from typing import Any, cast

import httpx

from app.agents.providers.base import (
    GenerationRequest,
    GenerationResult,
    LLMProvider,
    ProviderError,
)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self, *, base_url: str, model: str, embedding_model: str, timeout_seconds: int
    ) -> None:
        self.model = model
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_seconds)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        payload = self._payload(request, stream=False)
        data = await self._post("/api/chat", payload)
        message = cast(dict[str, Any], data.get("message", {}))
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("local model returned an empty response")
        return GenerationResult(
            content=content.strip(),
            model=str(data.get("model", self.model)),
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
            finish_reason=str(data.get("done_reason", "stop")),
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        try:
            async with self.client.stream(
                "POST", "/api/chat", json=self._payload(request, stream=True)
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield str(chunk)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ProviderError("unable to stream from the local model") from exc

    async def generate_structured(
        self, request: GenerationRequest, schema: dict[str, Any]
    ) -> dict[str, Any]:
        payload = self._payload(request, stream=False)
        payload["format"] = schema
        data = await self._post("/api/chat", payload)
        try:
            return cast(dict[str, Any], json.loads(data["message"]["content"]))
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("local model returned invalid structured output") from exc

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        data = await self._post("/api/embed", {"model": self.embedding_model, "input": list(texts)})
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise ProviderError("local model returned invalid embeddings")
        return cast(list[list[float]], embeddings)

    async def close(self) -> None:
        await self.client.aclose()

    def _payload(self, request: GenerationRequest, *, stream: bool) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "stream": stream,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_output_tokens,
            },
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self.client.post(path, json=payload)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(
                "local model is unavailable or returned an invalid response"
            ) from exc
