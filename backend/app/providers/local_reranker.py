"""本机 GPU 上的精排模型：Qwen3-Reranker（生成式，yes/no 概率）和 bge-reranker-v2-m3（交叉编码器）。

和嵌入模型一样，第一次调用才加载 torch 和模型。
"""

import asyncio
import importlib
import os
import threading
from pathlib import Path
from typing import Any

QWEN3_RERANK_INSTRUCTION = (
    "Given a web search query, retrieve relevant passages that answer the query"
)
# 模型卡里的提示词模板，要逐字照抄
QWEN3_PREFIX = (
    "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query "
    'and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n'
    "<|im_start|>user\n"
)
QWEN3_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
MAX_DOCUMENT_CHARS = 3000  # 文档先按字数截断；不能让分词器截断，否则会切掉后缀


def _quiet_hub() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class Qwen3Reranker:
    def __init__(
        self, name: str, model_id: str, *, device: str, batch_size: int, cache_dir: Path
    ) -> None:
        self.name = name
        self._model_id = model_id
        self._device = device
        self._batch_size = batch_size
        self._cache_dir = cache_dir
        self._loaded: tuple[Any, Any, Any] | None = None
        self._lock = threading.Lock()  # 并发调用时只加载一次，GPU 推理也排队

    def _load(self) -> tuple[Any, Any, Any]:
        if self._loaded is None:
            _quiet_hub()
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            tokenizer = transformers.AutoTokenizer.from_pretrained(
                self._model_id, padding_side="left", cache_dir=str(self._cache_dir)
            )
            model = transformers.AutoModelForCausalLM.from_pretrained(
                self._model_id, dtype=torch.float16, cache_dir=str(self._cache_dir)
            )
            self._loaded = (torch, tokenizer, model.to(self._device).eval())
        return self._loaded

    def _score(self, query: str, documents: list[str]) -> list[float]:
        torch, tokenizer, model = self._load()
        yes_id = tokenizer.convert_tokens_to_ids("yes")
        no_id = tokenizer.convert_tokens_to_ids("no")
        scores: list[float] = []
        for start in range(0, len(documents), self._batch_size):
            batch = documents[start : start + self._batch_size]
            texts = [
                f"{QWEN3_PREFIX}<Instruct>: {QWEN3_RERANK_INSTRUCTION}\n<Query>: {query}\n"
                f"<Document>: {document[:MAX_DOCUMENT_CHARS]}{QWEN3_SUFFIX}"
                for document in batch
            ]
            inputs = tokenizer(texts, padding=True, return_tensors="pt").to(self._device)
            with torch.no_grad():
                last = model(**inputs).logits[:, -1, :]
            pair = torch.stack([last[:, no_id], last[:, yes_id]], dim=1).float()
            scores += torch.softmax(pair, dim=1)[:, 1].tolist()
        return scores

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        return await asyncio.to_thread(self._locked_score, query, documents)

    def _locked_score(self, query: str, documents: list[str]) -> list[float]:
        with self._lock:
            return self._score(query, documents)


class CrossEncoderReranker:
    """bge-reranker-v2-m3：sentence-transformers 的 CrossEncoder，输出过 sigmoid 落在 0～1。"""

    def __init__(
        self, name: str, model_id: str, *, device: str, batch_size: int, cache_dir: Path
    ) -> None:
        self.name = name
        self._model_id = model_id
        self._device = device
        self._batch_size = batch_size
        self._cache_dir = cache_dir
        self._model: Any = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        if self._model is None:
            _quiet_hub()
            sentence_transformers = importlib.import_module("sentence_transformers")
            torch = importlib.import_module("torch")
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = sentence_transformers.CrossEncoder(
                self._model_id,
                device=self._device,
                cache_folder=str(self._cache_dir),
                model_kwargs={"dtype": torch.float16},
            )
        return self._model

    def _score(self, query: str, documents: list[str]) -> list[float]:
        with self._lock:
            return self._predict(query, documents)

    def _predict(self, query: str, documents: list[str]) -> list[float]:
        pairs = [(query, document[:MAX_DOCUMENT_CHARS]) for document in documents]
        scores = self._load().predict(
            pairs, batch_size=self._batch_size, show_progress_bar=False, convert_to_numpy=True
        )
        return [float(score) for score in scores]

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        return await asyncio.to_thread(self._score, query, documents)
