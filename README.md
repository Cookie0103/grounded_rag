# grounded_rag

Dify 官方中文文档的问答后端（RAG）：按问题复杂度选择检索流程，答案带引用，文档里没有就拒答。对外提供 REST API 和 MCP。

> 开发中。当前进度见 [docs/implementation-log](docs/implementation-log/README.md)，计划见 [docs/proposal-2026-10-15.md](docs/proposal-2026-10-15.md)。

## 快速开始

需要：[uv](https://docs.astral.sh/uv/)、Docker。Python 3.12 由 uv 自动安装。

```bash
cp .env.example .env              # 本机 5432 被占用时，见 .env.example 里关于 DB_PORT 的说明
docker compose up -d db           # PostgreSQL 16 + pgvector

cd backend
uv sync
uv run alembic upgrade head       # 迁移开发库
uv run poe check                  # 格式 + lint + 分层 + 类型 + 单元测试
uv run poe test-int               # 集成测试（自动建测试库 grounded_rag_test）
uv run poe serve                  # http://127.0.0.1:8000/health，接口文档 /docs
```

所有命令都在 `backend/` 下执行。

## 目录

```text
backend/    app/（业务代码）、tests/、eval/、scripts/、migrations/、pyproject.toml
docs/       计划、规范、Spec、决策记录、开发日志
data/       下载的原始文档（gitignore）
.cache/     临时内容、模型缓存（gitignore）
```

## 文档

| 想知道 | 看哪里 |
|---|---|
| 做什么、为什么、里程碑 | [docs/proposal-2026-10-15.md](docs/proposal-2026-10-15.md) |
| 代码、测试、接口、数据库规范 | [docs/coding-standards.md](docs/coding-standards.md) |
| 开发流程（Spec → Plan → Implement → Verify） | [docs/workflow.md](docs/workflow.md) |
| 当前里程碑的需求与验收 | [docs/specs/](docs/specs/) |
| 已定的决策 | [docs/decisions.md](docs/decisions.md) |
| 每天做了什么、遇到的问题 | [docs/implementation-log/](docs/implementation-log/README.md) |
| Agent 工作规则 | [AGENTS.md](AGENTS.md) |

## 许可

代码：MIT。Dify 文档（不入库）：CC BY 4.0，来源 [langgenius/dify-docs](https://github.com/langgenius/dify-docs)。
