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

网关在共享 Docker 网络内的地址为 `http://gateway:4000`。两个聊天模型使用 `/v1` 地址，嵌入配置以插件实际追加版本路径的行为为准。嵌入服务输出同一 MPS 模型的 1024 维向量。该接口为输入统一使用文档嵌入，LangGraph 的查询还带日文任务指令，判断检索对照时记录该差异。

## 语料和画布

从本机出题包解出 `documents/`，按原文件名导入 185 篇 S 档材料。文件名用于关联阶段 36 的金标 ID。预览一个正常分段后设置混合检索。导入 [Chatflow 模板](../../infra/dify/copilot-chatflow.yml)，将两个检索节点绑定同一知识库，再核对分类、泳道、HTTP、裁剪和回答节点。素材、实例导出与截图保存在本机忽略目录。

## 回放证据

先在本机分别预热两个系统，串行执行同一份开发用例。逐条的 Dify 意图、知识库命中、工具和最终回答留在回放目录。实际用量回调只写模型别名、请求 ID、时间和 token 数，文件位于 `.cache/litellm-usage/phase-37-gateway-usage.jsonl`。正式规程题准备与封存操作见[作者手册](copilot-author.md)。
