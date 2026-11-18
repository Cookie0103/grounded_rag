# grounded_rag

正在把现有问答后端改造成索尼银行住宅贷款坐席 Copilot 的概念验证。项目在本机运行，使用合成的客户与业务数据。项目目标、实现顺序和已验证进度分别见 [GOALS.md](GOALS.md)、[PLANS.md](PLANS.md) 和 [开发日志](harness/build-log.md)。

## 阶段 30 基础设施

需要 Python 3.12、uv、Docker Desktop 和 Ollama。首次运行时以 `.env.example` 为模板创建仓库根目录的 `.env`，填入 `DEEPSEEK_API_KEY` 和自行生成的 `GATEWAY_API_KEY`。有现成配置时补齐对应字段即可。Apple Silicon 上用 `EMBED_DEVICE=mps`。

```bash
ollama pull qwen3:4b-instruct
docker compose up -d --build --wait
cd backend
uv sync --locked --extra gpu
uv run poe check
uv run poe test-int
```

执行前在另一个终端用 `OLLAMA_CONTEXT_LENGTH=4096 ollama serve` 启动本机 Ollama，监听 11434 端口。网关启用方式为 `CHAT_MODEL=gateway`，大模型用 DeepSeek，小模型用 Ollama 的本机模型。容器端口、模型别名及覆盖方式见 [.env.example](.env.example)。

在 `backend/` 执行 `uv run python -m scripts.phase_30_models --gateway` 可验证两个档位及 token 用量。这会调用一次 DeepSeek，沿用本地每日预算。

第一版的运行与评测说明见 [归档 README](harness/archive/v1-dify-docs/README.md)。
