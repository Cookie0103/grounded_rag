"""本机 GPU 上的嵌入模型（sentence-transformers）：Qwen3-Embedding、bge-m3。

第一次调用才加载 torch 和模型，所以没装 gpu 依赖组的环境（包括 CI）也能 import 这个模块。
模型文件下载到 `.cache/models/`。
"""

import asyncio
import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import EMBEDDING_DIMENSION


@dataclass(frozen=True)
class EmbedderSpec:
    name: str  # 写进数据库 model 列的名字
    model_id: str  # Hugging Face 上的模型 ID
    query_instruction: str | None  # 只给查询加的指令；None 表示不加
    padding_side: str  # Qwen3-Embedding 取最后一个 token，要左填充；bge-m3 取第一个，要右填充


class SentenceTransformerEmbedder:
    def __init__(
        self, spec: EmbedderSpec, *, device: str, batch_size: int, cache_dir: Path
    ) -> None:
        self.name = spec.name
        self.dimension = EMBEDDING_DIMENSION
        self._spec = spec
        self._query_prompt = (
            f"Instruct: {spec.query_instruction}\nQuery:" if spec.query_instruction else None
        )
        self._device = device
        self._batch_size = batch_size
        self._cache_dir = cache_dir
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            # Windows 没开开发者模式时不能建符号链接，缓存会多占些空间；这条警告每次都出，关掉
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            sentence_transformers = importlib.import_module("sentence_transformers")
            torch = importlib.import_module("torch")
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = sentence_transformers.SentenceTransformer(
                self._spec.model_id,
                device=self._device,
                cache_folder=str(self._cache_dir),
                processor_kwargs={"padding_side": self._spec.padding_side},
                model_kwargs={"torch_dtype": torch.float16},
            )
        return self._model

    def _encode(self, texts: list[str], prompt: str | None) -> list[list[float]]:
        vectors = self._load().encode(
            texts,
            prompt=prompt,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector] for vector in vectors]

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts, self._query_prompt)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts, None)
