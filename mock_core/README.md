# 住宅贷款模拟业务服务

FastAPI 通过独立的 MySQL 8.4 提供住宅贷款只读查询。响应中的金额、利率、优惠、合同、个人资料和归属关系均为合成数据，业务查询响应包含 `synthetic: true`。商品名、金利类型和団信称谓沿用本机保存的公开词汇。

## 启动与种子校验

在仓库根目录启动并验证 Compose 服务。

```sh
docker compose up -d --build --wait mock_core
docker compose exec -T mock_core python -m mock_core.seed init
docker compose exec -T mock_core python -m mock_core.seed verify
```

服务在 8001 端口监听，启动时创建缺失的表并给空库灌入固定种子。重复运行 `init` 会校验现有记录的指纹，保留原有数据。`verify` 按主键导出全部业务表，比对数据库 SHA-256 和生成数据 SHA-256，同时输出场景统计。

在宿主机使用 Python 3.12 和发布到宿主机的 MySQL 时，在此目录运行以下命令。环境变量默认值见 [.env.example](.env.example)。

```sh
uv sync --locked
uv run --locked python -m pytest
MOCK_MYSQL_HOST=127.0.0.1 uv run --locked python -m mock_core.seed init
MOCK_MYSQL_HOST=127.0.0.1 uv run --locked python -m uvicorn mock_core.main:app --port 8001
```

可以离线比较同一种子的两次数据指纹。数据库校验通过 `verify` 完成。

```sh
uv run --locked python -m mock_core.seed fingerprint
uv run --locked python -m mock_core.seed fingerprint
```

## 联调用例

数据基准日固定为 2026-11-18。`A001` 和 `A020` 都拥有客户 `C0001` 的查询权限，`A002` 对该客户无查询权限。`C0001` 有两笔合同 `L0001` 和 `L0301`，其中 `L0001` 有 420 期还款记录。`C0002/L0002`、`C0003/L0003`、`C0004/L0004`、`C0005/L0005` 依次覆盖延滞、完済、固定期一年内到期和部分固定金利特約。

```sh
curl --fail http://127.0.0.1:8001/health
curl --fail -H 'X-Agent-Id: A001' \
  'http://127.0.0.1:8001/repayment-schedule?customer_id=C0001&contract_id=L0001&start_period=3&end_period=5'
```

还款区间两端均包含，省略端点时读取对应方向的全部期次。响应的 `total` 是请求区间内的明细数，还款概况按整笔合同计算。

## 故障注入

全局设置由 `MOCK_FAULT_DELAY_MS`、`MOCK_FAULT_TIMEOUT_RATE`、`MOCK_FAULT_5XX_RATE` 指定。概率采用 0 到 1，两类故障的概率之和最多为 1。单个接口可使用例如 `MOCK_FAULT_REPAYMENT_SCHEDULE_5XX_RATE=1` 覆盖全局设置。接口名对应 `AUTHORIZATION`、`LOAN_CONTRACTS`、`REPAYMENT_SCHEDULE`、`DELINQUENCY`、`RATE_TERMS`、`BENEFITS`。`MOCK_FAULT_SEED` 固定每个接口的故障序列，重启后按相同的鉴权成功请求顺序调用可重放。

设置 `MOCK_ALLOW_FAULT_HEADERS=true` 后，鉴权通过的请求可用 `X-Mock-Fault` 指定 `5xx`、`timeout` 或 `delay`。这些值分别返回 503、额外等待 5 秒后返回 504、延迟至少 250 毫秒后返回。健康检查始终直接读取数据库状态。

CI 和本机联调可以在启动 Compose 时设置 `MOCK_ALLOW_FAULT_HEADERS=true`。

```sh
MOCK_ALLOW_FAULT_HEADERS=true docker compose up -d --wait mock_core
curl -i -H 'X-Agent-Id: A001' -H 'X-Mock-Fault: 5xx' \
  'http://127.0.0.1:8001/loan-contracts?customer_id=C0001'
```

使用接口级变量时，把下面的配置保存到本机临时文件（例如 `/tmp/mock-core-faults.yaml`），作为 Compose override 载入。

```yaml
services:
  mock_core:
    environment:
      MOCK_FAULT_REPAYMENT_SCHEDULE_DELAY_MS: "300"
      MOCK_FAULT_REPAYMENT_SCHEDULE_5XX_RATE: "0.25"
```

```sh
docker compose -f docker-compose.yml -f /tmp/mock-core-faults.yaml up -d --wait mock_core
```
