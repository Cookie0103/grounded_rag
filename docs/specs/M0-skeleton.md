# M0：工程骨架

状态：已批准（作者 2026-10-16 确认，Sonnet 开始实现）

## 需求

### 目标

1. 在 `backend/` 建起可运行的最小工程：配置、错误格式、日志与 trace_id、`/health` 接口、数据库连接与迁移。
2. 质量门禁全部生效，违规时真的会失败：格式、lint、分层、类型、测试与覆盖率、pre-commit、CI。
3. 定义 `providers/` 的三个接口，并提供离线假实现，供后续里程碑在单元测试中使用。

### 非目标

- 不接 DeepSeek，不实现预算统计：等第一次真实调用 LLM 的里程碑（M4）再做。
- 不装 GPU 依赖（torch、sentence-transformers）：M1 再装。
- 不建业务表：M1 建。
- 不写后端的 Dockerfile：M7 再做。
- 不引入 LangGraph、MCP、bm25s 等后续才用的依赖。

### 接口与数据

- `GET /health`
  - 成功：200，`{"status": "ok", "database": "ok", "trace_id": "..."}`
  - 数据库不可用：503，`{"error": {"code": "DEPENDENCY_UNAVAILABLE", "message": "数据库不可用"}, "trace_id": "..."}`
- 所有响应都带 `X-Trace-Id` 响应头。请求如果带了 `X-Trace-Id`（只含字母、数字、短横线，长度不超过 64），就沿用它；否则生成 `uuid4().hex`。
- 统一错误格式（coding-standards §4）：

| 情况 | 状态码 | code |
|---|---|---|
| 参数校验失败 | 422 | `INVALID_REQUEST` |
| 路由不存在 | 404 | `NOT_FOUND` |
| `AppError` 子类 | 子类定义 | 子类定义 |
| 未捕获异常 | 500 | `INTERNAL_ERROR`（记录完整异常日志，响应里不暴露细节） |

- 配置项（仓库根目录 `.env`，模板为 `.env.example`）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://grounded:grounded@localhost:5432/grounded_rag` | |
| `DB_TIMEOUT_SECONDS` | `5` | 数据库操作超时 |
| `LOG_LEVEL` | `INFO` | |

- 迁移：`0001_enable_pgvector`，只执行 `CREATE EXTENSION IF NOT EXISTS vector`。
- 集成测试使用独立的数据库 `grounded_rag_test`（与开发库在同一个 PostgreSQL 实例里），由测试夹具自动创建并执行迁移。开发库只给人和 `poe ingest` 用，测试永远不碰它。

### 验收标准

| 编号 | 标准 | 验证方式 |
|---|---|---|
| AC1 | 干净 clone 后可以安装并通过全部检查 | `cd backend && uv sync && uv run poe check` 退出码为 0 |
| AC2 | 数据库能起，迁移能跑，集成测试通过 | `docker compose up -d db` 后，`uv run alembic upgrade head`（开发库）和 `uv run poe test-int`（测试库）都通过 |
| AC3 | 服务可启动，`/health` 行为符合上文 | `uv run poe serve` 后用 curl 请求；再停掉数据库请求一次，得到 503 和统一错误格式。命令和输出贴进当天日志 |
| AC4 | 门禁真的能拦住违规 | 对下面 5 种违规，各写一个临时文件，确认对应检查失败；输出贴进日志后删除临时文件，不提交：① `app/core` import `app/api`（lint-imports）；② `app/core` 里 `import openai`（ruff TID251）；③ `app/api` 里用 `os.environ`（TID251）；④ `print`（T20）；⑤ 缺少类型标注（mypy） |
| AC5 | 单元测试覆盖率 ≥ 80% | `poe check` 的输出 |
| AC6 | CI 两个 job 都通过 | 当天分支 push 后的 Actions 结果（`gh run list`），不需要开 PR |
| AC7 | pre-commit 生效；Claude Code 禁止编辑评测数据 | `uv run pre-commit run --all-files` 通过；`.claude/settings.json` 已提交 |
| AC8 | README 有快速开始 | 按 README 的步骤，从零能跑通 AC1～AC3 |

### 待确认

无。

**已决定的偏差（2026-10-16）**
- 本机 5432 已被 Windows 的 PostgreSQL 服务占用。docker-compose 的端口写成 `${DB_PORT:-5432}:5432`；本机 `.env` 里设 `DB_PORT=5433` 和对应的 `DATABASE_URL`。`Settings` 默认值仍是 5432（CI 用）。`DB_PORT` 只给 docker compose 用，不是 `Settings` 字段，所以 `.env.example` 一致性测试要把它列为例外。
- 作者暂不要求合并到 main，也不开 PR。CI 触发条件改为：任何分支 push 和 pull_request 都跑（原来只有 main 和 PR），这样不开 PR 也能看到 CI 结果。

## 方案

### 目录（M0 结束时）

```text
grounded_rag/
├── .claude/settings.json
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── .env.example
├── docker-compose.yml
├── README.md
└── backend/
    ├── .python-version          # 3.12
    ├── pyproject.toml
    ├── uv.lock
    ├── alembic.ini
    ├── migrations/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/0001_enable_pgvector.py
    ├── app/
    │   ├── __init__.py
    │   ├── core/      __init__.py  config.py  errors.py  logging.py  trace.py
    │   ├── providers/ __init__.py  base.py  fakes.py
    │   ├── db/        __init__.py  engine.py  tables.py
    │   └── api/       __init__.py  main.py  errors.py  health.py
    └── tests/
        ├── conftest.py
        ├── unit/
        │   ├── core/test_config.py
        │   ├── api/test_health.py
        │   ├── api/test_errors.py
        │   └── providers/test_fakes.py
        └── integration/test_database.py
```

不要建其他空目录或空模块。

### 关键设计

**配置（`app/core/config.py`）**

```python
REPO_ROOT = Path(__file__).resolve().parents[3]   # backend/app/core/config.py → 仓库根目录
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / ".cache"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://grounded:grounded@localhost:5432/grounded_rag"
    db_timeout_seconds: float = 5.0
    log_level: str = "INFO"

@lru_cache
def get_settings() -> Settings: ...
```

- `.env` 放在仓库根目录，docker compose 和后端共用一份。
- 单元测试里用 `Settings(_env_file=None)`，避免读到本机的 `.env`。
- `test_config.py` 里有一条测试：`.env.example` 中的变量名集合 = `Settings` 字段名（转大写）的集合。

**错误（`app/core/errors.py`）**

```python
class AppError(Exception):
    code = "INTERNAL_ERROR"
    status_code = 500
    def __init__(self, message: str) -> None: ...

class DependencyUnavailableError(AppError):
    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503
```

以后需要新的错误码，就加子类，不在别处写状态码。

**trace_id 与日志（`app/core/trace.py`、`app/core/logging.py`）**

- `trace.py`：`trace_id_var: ContextVar[str]`，以及 `new_trace_id() -> str`。
- `logging.py`：`configure_logging(level: str)`。加一个 `logging.Filter`，把 `trace_id` 写进每条日志记录。格式为 `%(asctime)s %(levelname)s %(name)s trace=%(trace_id)s %(message)s`。

**API（`app/api/`）**

- `main.py`：`create_app() -> FastAPI`。在 lifespan 里创建引擎并放到 `app.state.engine`，关闭时 `dispose()`；注册 trace 中间件、错误处理和 health 路由。启动命令：`uvicorn app.api.main:create_app --factory`。
- `errors.py`：4 个异常处理器（见上方表格）。
- `health.py`：数据库检查通过依赖注入 `Annotated[DatabasePing, Depends(get_database_ping)]` 获得，单元测试用 `app.dependency_overrides` 替换成假实现。FastAPI 依赖一律用 `Annotated` 写法，这样不会触发 ruff 的 B008。

**数据库（`app/db/`）**

- `engine.py`：
  - `create_engine(settings) -> AsyncEngine`
  - `async def ping(engine, timeout: float) -> None`：用 `asyncio.timeout` 包住 `SELECT 1`，任何失败都转成 `DependencyUnavailableError`
- `tables.py`：只放 `metadata = MetaData()`，M1 在这里加表。
- 迁移：在 `backend/` 下用 `uv run alembic init -t async migrations` 生成，再改 `env.py`：调用方通过 `config.set_main_option("sqlalchemy.url", ...)` 传了连接串就用它（测试夹具这样传），否则用 `get_settings().database_url`；`target_metadata = metadata`。迁移文件用 `--rev-id 0001` 生成。
- 测试夹具（`tests/integration/conftest.py`）：
  - `test_database_url`：把 `Settings().database_url` 的库名换成 `grounded_rag_test`（用 `sqlalchemy.engine.make_url(...).set(database=...)`）
  - session 级夹具：用 AUTOCOMMIT 连接 `postgres` 库，库不存在就执行 `CREATE DATABASE grounded_rag_test`；然后用 `alembic.command.upgrade(cfg, "head")` 迁移到最新版本
  - `engine` 夹具：返回连测试库的 `AsyncEngine`，用完 `dispose()`
  - M1 加表以后，再加一个每个测试前 `TRUNCATE ... CASCADE` 的夹具

**providers（`app/providers/`）**

`base.py`：

```python
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class Completion(BaseModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int

class ChatModel(Protocol):
    async def complete(self, messages: list[ChatMessage], *, json_mode: bool = False) -> Completion: ...

class Embedder(Protocol):
    name: str
    dimension: int
    async def embed_queries(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

class Reranker(Protocol):
    name: str
    async def rerank(self, query: str, documents: list[str]) -> list[float]: ...   # 每个文档一个 0～1 分数，顺序与输入一致
```

查询和文档的嵌入要分开，原因见 [RAG 笔记 §2](../implementation-log/2026-10-16/notes-rag.md)：Qwen3-Embedding 只给查询加指令。

`fakes.py`：所有假实现都是确定性的，并且有“语义”，这样 M2 的检索测试才有意义。

- 公共函数 `char_bigrams(text) -> set[str]`：去掉空白后的字符二元组。
- `FakeEmbedder(dimension=1024)`：对每个二元组计算 `int(sha1(bigram).hexdigest(), 16) % dimension`，在对应维度上 +1，最后做 L2 归一化。字面越相似的文本，余弦相似度越高。查询和文档用同一种算法。
- `FakeReranker`：分数 = 查询和文档二元组集合的 Jaccard 相似度。
- `FakeChatModel(responses: list[str] | None = None)`：按顺序返回预设的回答；没有预设时返回最后一条 user 消息。token 数用 `len(text) // 2` 估算。调用记录保存在 `self.calls`，供测试断言。

### 配置文件内容

`backend/pyproject.toml` 的工具部分如下。依赖用 `uv add` 添加，不要手写版本号：

- 运行依赖：`uv add fastapi "uvicorn[standard]" pydantic pydantic-settings "sqlalchemy[asyncio]" asyncpg alembic pgvector`
- 开发依赖：`uv add --dev ruff mypy pytest pytest-asyncio pytest-cov poethepoet import-linter pre-commit httpx`

```toml
[project]
name = "grounded-rag"
version = "0.1.0"
requires-python = ">=3.12,<3.13"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "C90", "ASYNC", "S", "BLE", "T20", "ERA", "PL", "PT", "RUF", "TID"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-statements = 40

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"os.environ".msg = "配置只在 app/core/config.py 读取"
"os.getenv".msg = "配置只在 app/core/config.py 读取"
"openai".msg = "外部模型只能经过 app/providers/"
"httpx".msg = "外部调用只能经过 app/providers/"
"torch".msg = "模型推理只能经过 app/providers/"
"transformers".msg = "模型推理只能经过 app/providers/"
"sentence_transformers".msg = "模型推理只能经过 app/providers/"

[tool.ruff.lint.per-file-ignores]
"app/core/config.py" = ["TID251"]
"app/providers/**" = ["TID251"]
"tests/**" = ["S101", "PLR2004", "TID251"]
"migrations/**" = ["ERA001"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["app", "tests"]
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
addopts = "--strict-markers"
markers = ["integration: 需要 PostgreSQL（docker compose up -d db）"]

[tool.coverage.run]
source = ["app"]
branch = true
omit = ["app/db/*"]          # 数据库代码由集成测试覆盖

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = true

[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "分层依赖方向（coding-standards §3）"
type = "layers"
layers = [
    "app.api",
    "app.providers | app.db",
    "app.core",
]

[tool.poe.tasks]
fmt = [{ cmd = "ruff format ." }, { cmd = "ruff check --fix ." }]
lint = [{ cmd = "ruff format --check ." }, { cmd = "ruff check ." }, { cmd = "lint-imports" }]
typecheck = "mypy"
test = "pytest -m 'not integration' --cov --cov-report=term-missing"
check = ["lint", "typecheck", "test"]
test-int = "pytest -m integration"   # 测试库由夹具创建并迁移
serve = "uvicorn app.api.main:create_app --factory --reload"
```

注意：
- 以后新增模块时，按 coding-standards §3 的方向把它加进 `layers`。这属于落实已定规则，不算“改检查配置”，不用先问。`eval` 在 M3 加入 `files` 和 `coverage.source`。
- `"app.providers | app.db"` 表示这两层同级、互不依赖。如果当前 import-linter 版本不支持 `|` 写法，查官方文档换成等价写法，并在日志里记一笔。
- ruff 的 `banned-api` 写的是模块名，要用 AC4 确认 `from openai import X` 这种写法也会被拦住；拦不住就查 ruff 文档调整，并记在日志里。

`.pre-commit-config.yaml`（仓库根目录）：

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.1            # 与 uv.lock 里的 ruff 版本一致
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0             # 用 pre-commit autoupdate 取最新版本
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
        args: [--maxkb=1000]
```

ruff 会自动找离文件最近的 `backend/pyproject.toml`，从仓库根目录运行也能用上正确的配置。安装方式：在 `backend/` 下执行 `uv run pre-commit install`。

`.claude/settings.json`（仓库根目录）：

```json
{
  "permissions": {
    "deny": ["Edit(/backend/eval/data/**)", "Write(/backend/eval/data/**)"]
  }
}
```

路径规则写法以 Claude Code 文档为准：以 `/` 开头，表示相对于设置文件所在的项目根目录。

`docker-compose.yml`（仓库根目录）：

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: grounded
      POSTGRES_PASSWORD: grounded
      POSTGRES_DB: grounded_rag
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U grounded -d grounded_rag"]
      interval: 5s
      timeout: 5s
      retries: 10
volumes:
  pgdata:
```

`.github/workflows/ci.yml`：

```yaml
name: CI
on:
  push:                 # 任何分支；作者暂不开 PR，靠 push 触发
  pull_request:
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
defaults:
  run:
    working-directory: backend
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6        # 用当时的最新主版本
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock
      - run: uv sync --locked
      - run: uv run poe check
  integration:
    runs-on: ubuntu-latest
    services:
      db:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: grounded
          POSTGRES_PASSWORD: grounded
          POSTGRES_DB: grounded_rag
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U grounded -d grounded_rag"
          --health-interval 5s --health-timeout 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock
      - run: uv sync --locked
      - run: uv run poe test-int
```

CI 用的数据库连接串与 `Settings` 的默认值一致，所以不需要设置环境变量。

### 测试清单

| 文件 | 测什么 |
|---|---|
| `unit/core/test_config.py` | 默认值；环境变量覆盖（用 `monkeypatch.setenv`）；`.env.example` 与字段一致 |
| `unit/api/test_health.py` | 数据库正常时返回 200 及字段；ping 抛 `DependencyUnavailableError` 时返回 503 和统一格式；响应头有 `X-Trace-Id`；合法的请求 trace_id 被沿用；非法的被替换 |
| `unit/api/test_errors.py` | 422、404、500 都是统一格式；500 响应不含异常细节（测试里临时挂一个会抛异常的路由） |
| `unit/providers/test_fakes.py` | 嵌入是确定性的且已归一化；相似文本的余弦相似度高于不相似文本；精排分数在 0～1，且相关文档排在前面；ChatModel 按顺序返回预设回答并记录调用 |
| `integration/test_database.py` | 测试库迁移后 `vector` 扩展存在；用连接测试库的真实引擎请求 `/health` 返回 200（把引擎放进 `app.state.engine`） |

单元测试用 `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")` 调接口。

## 任务

- [ ] T1 后端工程初始化：`backend/.python-version`、pyproject、依赖、`app/core/`（config、errors、trace、logging）及测试 → AC1 的一部分
- [ ] T2 质量门禁：ruff、mypy、import-linter、pytest、覆盖率、poe 任务；`.pre-commit-config.yaml`；`.claude/settings.json`；逐条验证违规会被拦住 → AC4、AC7
- [ ] T3 providers：三个接口与假实现及测试 → AC5
- [ ] T4 数据库：docker-compose、engine、alembic、0001 迁移、集成测试 → AC2
- [ ] T5 API：create_app、trace 中间件、统一错误、`/health` 及测试 → AC3
- [ ] T6 CI 与 README：`ci.yml`；README 写项目一句话介绍、快速开始（启动数据库、安装、检查、运行）、目录说明、文档索引 → AC6、AC8
- [ ] T7 收尾：完整跑一遍 `poe check` 和 `poe test-int`，做一次对抗性自审（workflow §4.3），写日志，推送（暂不开 PR）

## 阻塞

## 记录
