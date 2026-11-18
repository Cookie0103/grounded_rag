# 阶段 30 运行环境和选型（2026-11-18）

- 作者改用当前 Mac 完成第二版，主机为 macOS 27.2.1（arm64）、Apple M4 Max、64 GB 统一内存。Docker Desktop 4.90.0，Engine 29.7.2。Docker 内存上限设为 24 GiB，`docker info` 报告虚拟机可见 25,158,770,688 字节，架构 `aarch64`。这一变更同步至 GOALS 和 PLANS，以实际运行环境为准。[Docker Desktop 资源设置](https://docs.docker.com/desktop/settings-and-maintenance/settings/)
- Qwen3-Embedding-0.6B 和 Qwen3-Reranker-0.6B 在 macOS 主机的 MPS 上运行。PyTorch 2.14.1 的 MPS 张量运算成功；用仓库缓存权重调用现有工厂完成一次日文嵌入和一次精排。嵌入返回 1024 维，含加载耗时 6.399 秒；精排相关片段得分 0.99993，高于无关片段的 0.00004，含加载耗时 1.248 秒。这两个时间来自单次含加载的运行。
- 意图档选定 Qwen3 4B Instruct Q4_K_M（`0edcdef34593`），由本机 Ollama 0.40.16 的 Metal 路径运行。Ollama 初次自动分配 262144 token 上下文时报告占用 42 GB，改用 `OLLAMA_CONTEXT_LENGTH=4096` 后占用 3.2 GB。两款候选的公平比较见[阶段 30 实测](../build/phase-30-cleanup-infra.md#记录)。[Qwen3 4B Instruct](https://ollama.com/library/qwen3:4b-instruct) · [Qwen2.5 7B](https://ollama.com/library/qwen2.5:7b)
- 生成档通过本地 LiteLLM 1.110.0 调用 DeepSeek V4 Pro。按厂商高峰、缓存未命中的 Pro 单价和实际返回 token 做保守预算记账，沿用原每日 ¥10 上限。[DeepSeek 模型与单价](https://api-docs.deepseek.com/quick_start/pricing/)
- 第一版的 P95 18～32 秒来自 Windows、RTX 5070 Ti 环境，只作历史背景。阶段 37 在同一台 Mac 上让 Dify 与 LangGraph 使用相同用例、网关和模拟业务服务，报完整同题实测。Dify 按常规配置分段、混合检索、分类器说明和少样本示例，配置完成后直接回放。
- `uv --no-config lock --check --offline` 从 `backend/` 运行成功，解析 160 个包。普通 `--locked` 被本机全局 `exclude-newer` 拦住；后续校验通过单次命令忽略本机 uv 配置，不改全局文件和锁文件。
- Homebrew 安装 Ollama 时同时更新了它的依赖和 Homebrew 的 `python3` 链接。本项目仍由 uv 使用 Python 3.12.13。权重缓存于 `.cache/ollama/models`。
