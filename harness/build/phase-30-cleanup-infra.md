# 阶段 30：清场与基础设施

状态：未开始（草案；执行模型开工前可细化，细化后自行标「已批准」）

> 这是计划和记录，不是完成证据；进度以 [build-log](../build-log.md) 为准。设计依据见 [PLANS.md](../../PLANS.md) §1、§2、§4.6。

## 需求

### 目标

1. 把第一版（Dify 文档问答）专属的内容归档或删除，让仓库里不再有两套互相矛盾的说明。
2. 本地基础设施一条命令起齐：PostgreSQL（已有）、Elasticsearch（带 kuromoji）、Redis、MySQL、模型网关。
3. 选定并跑通小模型档，确认问答服务能经网关调用大小两档模型。

### 非目标

- 任何业务逻辑改动（语料、检索、编排都在后面的阶段）。
- 启动 Dify（阶段 37 才起）。

### 验收标准

| 编号 | 标准 | 验证 |
|---|---|---|
| AC1 | 第一版专属文档已归档到 `harness/archive/v1-dify-docs/`，根目录与 `docs/` 不再出现 Dify 文档问答的说明 | `git status`、目录清单 |
| AC2 | `docker compose up -d` 后五个服务全部 healthy | `docker compose ps` 输出 |
| AC3 | ES 能用 kuromoji 分词日文 | `_analyze` 一句日文，输出词元 |
| AC4 | 经网关各调用一次小模型和大模型，返回正常且有 token 用量 | 脚本输出 |
| AC5 | 小模型的意图分类单次耗时有实测值 | 20 次调用的中位数与 P95 |
| AC6 | `uv run poe check` 通过 | 命令输出摘要 |

## 任务

- [ ] T1 归档：`导学-grounded-rag.md`、`面经-grounded-rag.md`、`docs/eval/`、`docs/final-report-template.md`、`backend/eval/reports/` 用 `git mv` 移到 `harness/archive/v1-dify-docs/`。`README.md` 顶部先加一段「正在改造为第二版」的说明，正文留到阶段 38 重写。
- [ ] T2 标记待替换代码：`scripts/fetch_docs.py`、`scripts/export_for_gemini.py`、`ingest/fetch.py`、`eval/smoke_retrieval.jsonl` 等只服务 Dify 语料的文件，本阶段只在记录里列清单，不删；删除放到替代实现落地的阶段。
- [ ] T3 compose：新增 `es`（自建镜像，装 `analysis-kuromoji`，单节点、关安全认证、堆内存设 1g）、`redis`、`mysql`、`gateway`（LiteLLM Proxy，配置文件入库、密钥走 `.env`）。全部带 healthcheck，端口可用环境变量覆盖。
- [ ] T4 配置：`core/config.py` 与 `.env.example` 增加 ES、Redis、MySQL、网关地址与 key、大小模型名。
- [ ] T5 小模型：在本机 GPU 上用 Ollama 或 vLLM 起一个 4B 量级的模型，注册进网关。候选至少比较两个，按「日文意图分类冒烟题 20 条的准确率」和显存占用选一个。带不动就把小模型档指向 `deepseek-flash` 并记录。
- [ ] T6 `providers/`：新增走网关的对话客户端（先只要非流式 `complete`，流式放阶段 35），假实现同步；工厂按档位（`small` / `large`）取模型。预算与记账沿用现有逻辑。
- [ ] T7 文档：`PROMPTS.md` 里与 Dify 文档强绑定的段落标注「第一版，待阶段 36 更新」。

## 需要作者做的

无。若本机显存不足以同时放嵌入、精排和小模型，在记录里写明实测占用和最终取舍。

## 记录

（执行时填写：选了哪个小模型及理由、各容器内存占用、遇到的坑）

## 阻塞

（无）
