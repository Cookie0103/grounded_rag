# 本机 Dify 对照运行手册

本机对照固定 Dify 1.19.0，官方源码放在 `.cache/dify-1.19.0/`。小模型、嵌入、向量库和工作流留在本机，DeepSeek 生成经已有网关访问外部 API。官方版本与 Compose 来源见 [Dify 1.19.0](https://github.com/langgenius/dify/releases/tag/1.19.0)。

## 启动

在仓库根目录启动共同的模拟业务和网关。

```bash
docker compose up -d --build --wait
git clone --depth 1 --branch 1.19.0 https://github.com/langgenius/dify.git .cache/dify-1.19.0
```

在 `backend/` 启动供 LiteLLM 使用的 MPS 嵌入服务。

```bash
uv run --locked uvicorn scripts.dify_embeddings:create_app --factory --host 127.0.0.1 --port 18082
```

Dify 使用独立 `grounded_dify` 项目。准备脚本从官方模板写入本机容器间密钥，已有配置会保留。覆盖文件允许工作流访问本次对照所需的网关和只读模拟业务。

```bash
python3 infra/dify/prepare.py .cache/dify-1.19.0/docker
cd .cache/dify-1.19.0/docker
docker compose -p grounded_dify -f docker-compose.yaml \
  -f ../../../infra/dify/compose.override.yml up -d --wait
```

控制台地址为 `http://127.0.0.1:18090/install`。首次使用专用本机测试管理员。账户口令和 Chatflow API Key 仅保存在忽略的 `.env`。Dify 里的供应商选择官方 [OpenAI-API-compatible](https://marketplace.dify.ai/plugin/langgenius/openai_api_compatible)，聊天模型、嵌入和用途如下。

| 网关别名 | 用途 |
|---|---|
| `small` | 本机日文问题分类 |
| `deepseek-v4-pro` | 坐席与客户最终生成 |
| `qwen3-embedding-0.6b` | 本机 S 档索引和查询嵌入 |

网关在共享 Docker 网络内的地址为 `http://gateway:4000`。OpenAI 兼容插件 0.0.84 的三个模型均使用 `http://gateway:4000/v1` 作为基础地址。嵌入服务输出同一 MPS 模型的 1024 维向量。Dify 查询复用文档嵌入，LangGraph 的查询还带日文任务指令，检索对照须记录这个差异。

## 语料和画布

从本机出题包解出 `documents/`，按原文件名导入 185 篇 S 档材料。文件名用于关联阶段 36 的金标 ID。采用通用分段，空行分隔，上限 1024 字符，重叠 50 字符。高质量索引选择本机 Qwen3，混合检索用语义 0.7、关键词 0.3、Top 5。导入 [Chatflow 模板](../../infra/dify/copilot-chatflow.yml)，将两个检索节点各绑定同一知识库一次。通过检查清单后，从工作区发布到本机。素材、实例导出与截图保存在本机忽略目录。

## 回放证据

在已发布应用的「访问入口 → 后端服务 API」使用本机专用密钥，放入项目忽略的 `.env` 中 `DIFY_API_KEY`。导出实际使用的应用包，从中取出 `app.yaml` 作为回放清单的画布输入。先在本机分别预热两个系统，串行执行同一份开发用例。逐条的 Dify 意图、知识库命中、工具和最终回答留在回放目录。实际用量回调只写模型别名、请求 ID、时间和 token 数，文件位于 `.cache/litellm-usage/phase-37-gateway-usage.jsonl`。正式规程题准备与封存操作见[作者手册](copilot-author.md)。

当前 Mac 的画布导出为 `.cache/dify-evidence/published-chatflow.yml`。在仓库根目录先用 `MOCK_ALLOW_FAULT_HEADERS=true docker compose up -d --wait mock_core` 启用明确指定的合成故障，然后从 `backend/` 执行基线回放。

```bash
uv run --locked python -m scripts.compare_dify \
  --dify-url http://127.0.0.1:18090/v1 \
  --chatflow ../.cache/dify-evidence/published-chatflow.yml \
  --run-dir ../.cache/copilot-eval/runs/mac-dify-baseline \
  --langgraph-run ../.cache/copilot-eval/runs/mac-baseline \
  --warmup 2 --langgraph-warmup 2 --hardware 'Mac M4 Max / 64 GB / Docker 24 GiB' \
  --same-machine --same-gateway --embedding same --embedding-model qwen3-embedding-0.6b
```

随机故障回放使用同一代码、语料、模型和用例，先从仓库根目录执行 `MOCK_ALLOW_FAULT_HEADERS=false docker compose -f docker-compose.yml -f infra/mock-faults-5pct.yml up -d --wait mock_core`。回放命令改用 `--fault-mode 5%-timeout`、独立 `--run-dir ../.cache/copilot-eval/runs/mac-dify-fault-5pct` 和 `--langgraph-run ../.cache/copilot-eval/runs/mac-fault-5pct`，固定种子一致后添加 `--same-fault-profile`。最后在基线命令中加 `--report-only --merge-fault-run ../.cache/copilot-eval/runs/mac-dify-fault-5pct` 和故障条件的第二个 `--langgraph-run`。停止回放后恢复 `MOCK_ALLOW_FAULT_HEADERS=false docker compose -f docker-compose.yml up -d --wait mock_core`。
