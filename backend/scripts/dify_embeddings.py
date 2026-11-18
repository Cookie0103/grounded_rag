"""通过同一 LiteLLM 网关向 Dify 暴露本机 MPS 嵌入模型。"""

import base64
import struct
from hmac import compare_digest
from typing import Annotated, Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from app.core.config import Settings, get_settings
from app.providers.factory import get_embedder
from app.providers.local_embedder import SentenceTransformerEmbedder

Text = Annotated[str, StringConstraints(min_length=1, max_length=24_000)]


class EmbeddingRequest(BaseModel):
    model: str
    input: Text | Annotated[list[Text], Field(min_length=1, max_length=128)]
    encoding_format: Literal["float", "base64"] = "float"
    dimensions: int | None = None


def _embedding(values: list[float], encoding_format: str) -> list[float] | str:
    if encoding_format == "base64":
        return base64.b64encode(struct.pack(f"<{len(values)}f", *values)).decode("ascii")
    return values


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    provider = get_embedder(config.embedding_model, config)
    if not isinstance(provider, SentenceTransformerEmbedder):
        raise RuntimeError("Dify 嵌入服务需要配置本机 transformers 嵌入模型")
    app = FastAPI(title="grounded_rag 本机嵌入")

    @app.post("/v1/embeddings")
    async def embeddings(
        body: EmbeddingRequest, authorization: Annotated[str, Header()] = ""
    ) -> dict[str, object]:
        key = config.gateway_api_key
        if not key or not compare_digest(authorization.encode(), f"Bearer {key}".encode()):
            raise HTTPException(status_code=401, detail="嵌入服务需要网关认证")
        if body.model != provider.name or body.dimensions not in {None, provider.dimension}:
            raise HTTPException(status_code=422, detail="嵌入模型或维度不受支持")
        texts = [body.input] if isinstance(body.input, str) else body.input
        vectors = await provider.embed_documents(texts)
        tokens = await provider.document_tokens(texts)
        return {
            "object": "list",
            "model": provider.name,
            "data": [
                {
                    "index": i,
                    "object": "embedding",
                    "embedding": _embedding(vector, body.encoding_format),
                }
                for i, vector in enumerate(vectors)
            ],
            "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
        }

    return app
