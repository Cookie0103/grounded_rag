# 阶段18：Windows评测前运行决策

- 2026-10-20：本轮实际主机为Windows、RTX 5070 Ti。先前build-log的Mac/MPS是另一环境的历史记录；本次以[实测报告](phase-18-readiness-report.json)为准。
- Docker Desktop起初未运行。启动错误先后指向`%LOCALAPPDATA%/Docker/run/dockerInference`及`%LOCALAPPDATA%/docker-secrets-engine/engine.sock`。失败启动会留下另一目录的socket；在结束本轮失败实例后，同时备份两个临时目录再启动成功。没有重置Desktop、删卷或改引擎配置。
- 保留的可恢复备份：`Docker/run.grounded-rag-20261020-192208`、`Docker/run.grounded-rag-20261020-192451`、`docker-secrets-engine.grounded-rag-20261020-backup`、`docker-secrets-engine.grounded-rag-20261020-192451`（均相对于`%LOCALAPPDATA%`）。具体末次备份名以本机实际目录为准；不依赖备份运行。
- 只启动原有`grounded_rag-db-1`；5432、语料、向量及迁移保持原样。未主动启动其他项目容器。
- REST绑定`127.0.0.1:8000`，不启用reload，进程环境临时设置`PREWARM=true`、`HF_HUB_OFFLINE=1`、`PYTHONUTF8=1`。保留根`.env`、CUDA、batch、模型与每日预算设置；SDK凭据不输出、不提交。
- Langfuse既验证认证，也验证真实上传和读回。独立连接检查明确命名为`readiness-connectivity-check`；随后真实RAG trace的根输出与本地回答一致，并读回全部步骤。实际候选和生成上下文保存在本地及云端原始观测中。
- 检查针对带有既有未提交修改的当前工作区；本任务不宣称这些修改已审核或题集已冻结。正式性能测试应分别统计冷启动、正常生成、重生成及缓存命中，单次探针仅证明链路可用。
