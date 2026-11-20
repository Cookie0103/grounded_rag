# 住宅贷款规程评测作者手册

## 准备开发题和封存题

使用阶段 31 的本机出题包 `.cache/policy-question-pack.zip`。包中的 `index.jsonl` 提供带版本的 `document_id`、生效区间和 `synthetic` 标记，`documents/` 保存供核对的正文。出题包和题目均留在本机，公开页面快照按其使用条件处理。封存题和封存运行目录从创建起就放在仓库之外，由作者保管。

作者让独立于开发模型和被测模型的模型分两批出题，再由另一个模型审题。开发集约 40 题，其中约 8 道版本陷阱、5 道不可回答题。封存集约 20 题，其中约 4 道版本陷阱、3 道不可回答题。两批题不重复场景或问法，审完后只把开发集交给项目执行模型。审题模型核对证据、适用日期、关键点和不可回答类别，封存题只在作者控制的环境中审阅。

### 日文出题提示

```text
住宅ローンの問い合わせ対応を評価するための設問を、日本語で作成してください。
添付資料の index.jsonl と documents/ だけを根拠にし、各文書の document_id、
適用開始日・終了日、synthetic の印を確認してください。依頼ごとに開発用か封印用の
いずれか一方を作り、指定件数、設問 ID の接頭辞、split を守ってください。

設問は、資料を見ていない利用者が単独で読んで理解できる自然な問い合わせにしてください。
資料の見出しを写すだけの言い回しや、回答を誘導する引用は避けてください。単独の資料で
判断できる設問、複数の資料の突き合わせが必要な設問、適用時点で回答が変わる設問、
資料だけでは回答できない設問を含めてください。実在する個人の情報は使いません。

回答可能な設問には、index.jsonl にある版付きの document_id を gold_docs に入れ、
解答の要点を nuggets に二つから四つ書いてください。各要点に text と importance を付け、
最低一つは vital、補足は okay とします。二つ以上の資料が必要な場合はそのすべてを挙げて
ください。同じ要点を裏付ける代替資料がある場合は、gold_doc_groups の同じグループに
入れてください。すべてのグループから一つ以上の資料が必要です。

適用時点で回答が変わる設問は version_trap を true にし、as_of に YYYY-MM-DD 形式の
照会基準日を入れてください。基準日に適用される版を金標にしてください。質問自体にも
基準日が読み取れるように書いてください。失効した版、草案、将来版は根拠に含めません。

回答不能な設問には unanswerable_category を指定し、gold_docs と nuggets を空にします。
値は out_of_database（資料に情報なし）、out_of_scope（対象外）、injection（指示の上書き）、
false_premise（誤った前提）、underspecified（必要な情報の不足）のいずれかです。
資料で矛盾を確認できる誤った前提は、質問に自然に含めてください。

架空の文書、運用、金利、顧客などを根拠や題材にした場合は synthetic を true にして、
実在する銀行の内部運用や金利として書かないでください。category は policy とします。
出力は UTF-8 の JSONL で、1 行に 1 問の JSON オブジェクトを書いてください。
コードフェンス、説明、引用した資料本文は出力しないでください。
```

给出题模型追加批次参数 `開発用、約40問、IDはpolicy-dev-、splitはdev` 或 `封印用、約20問、IDはpolicy-test-、splitはtest`。审题模型可用下面的检查提示。

```text
各設問について、他の設問との重複、自然な日本語、金標文書 ID の実在性、適用基準日に
選んだ版の有効性、vital 要点の根拠、回答不能カテゴリ、synthetic の印を確認してください。
修正が必要な設問は設問 ID と修正箇所を返し、資料本文は出力しないでください。
```

### 输出格式

开发用 UTF-8 JSONL，例如 `.cache/copilot-policy-dev.jsonl`。下面的 ID 和题目是格式示例，正式题使用包内的真实索引 ID。

```jsonl
{"id":"policy-dev-001","category":"policy","split":"dev","synthetic":true,"question":"架空の変更手続きは2026年10月1日に郵送で申し込めますか？","as_of":"2026-10-01","version_trap":true,"gold_docs":["synthetic/example@v2"],"nuggets":[{"text":"郵送で申し込める","importance":"vital"},{"text":"架空の申請書を同封する","importance":"okay"}]}
```

封存用单独的 UTF-8 JSONL，例如仓库外的 `policy-test.jsonl`。使用 `split: "test"` 及独立题目 ID。

```jsonl
{"id":"policy-test-001","category":"policy","split":"test","synthetic":true,"question":"架空の手続きで一次審査員の当日の当番を教えてください。","unanswerable_category":"out_of_scope","gold_docs":[],"nuggets":[]}
```

## 校准评审

从 `backend/` 执行。将 `REVIEW_COMMAND` 设为作者选定的非 DeepSeek 评审命令，它应从标准输入读提示并向标准输出返回 JSON。选择符合语料使用条件的模型运行环境，记录模型和版本。评测从本机出题包读取金标正文，正式报告只记录指标和错误归因。

```bash
uv run python -m scripts.evaluate_copilot \
  --policy-dev ../.cache/copilot-policy-dev.jsonl \
  --run-dir ../.cache/copilot-dev \
  --judge-command "$REVIEW_COMMAND" --prepare-calibration
```

1. 先打开运行目录下的 `author-calibration-blind.jsonl`，用实际回答、题目、日期与本机金标独立标 20 条。能按原样发送标 `true`，需要修改标 `false`。检查必要条件、日期和版本是否准确，是否有无依据的说法，不可回答时是否按类别澄清、纠正或拒答。
2. 标完再打开 `author-calibration.jsonl`，按 `id` 将人工结果填入 `human_acceptable`。每个 ID 只出现一次，两种标签都用 JSON 布尔值。现有评审先给关键点和行为标签，再用既有评分判定。可回答题须完整覆盖必要关键点且无矛盾，不可回答题须符合类别要求。
3. 至少 20 条有效样本且一致率达到 85% 才能采用此评审。20 条时至少 17 条一致。校准缺失或未达门槛时，规程评分和离线可采纳率显示「未测」。离线可采纳率衡量模型评审认为可原样发送的规程回答比例，真实坐席的采纳率仍为「未测」。

```jsonl
{"id":"policy-dev-001","human_acceptable":true,"judge_acceptable":false}
```

用同一评审命令和同一开发运行目录生成正式开发报告。`--resume` 接续该目录内已经记录的请求。

```bash
uv run python -m scripts.evaluate_copilot \
  --policy-dev ../.cache/copilot-policy-dev.jsonl \
  --run-dir ../.cache/copilot-dev --resume \
  --judge-command "$REVIEW_COMMAND" \
  --calibration ../.cache/copilot-dev/author-calibration.jsonl
```

## 作者运行一次封存评测

由作者本人操作。冻结提交是 `fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0`，原机本地标签为 `copilot-freeze-2026-11-20`。封存运行使用原 S/L 语料快照、同一模型别名和原配对校准文件。换机时先恢复这些本机材料，方法见 [换机手册](../retrospective/migration.md)。

### 运行前核对

1. 从交接分支的仓库根目录执行 `git diff --exit-code fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0 -- backend mock_core infra docker-compose.yml .env.example`。无输出且退出码为 0 时，当前运行文件与冻结提交一致。
2. 根目录本机 `.env` 沿用 `CHAT_MODEL=gateway`、`GATEWAY_BASE_URL`、`GATEWAY_API_KEY`、`DEEPSEEK_API_KEY`、`GATEWAY_SMALL_MODEL=small`、`GATEWAY_LARGE_MODEL=deepseek-v4-pro`、`EMBEDDING_MODEL=qwen3`、`EMBED_DEVICE=mps`、`DATABASE_URL`、`ELASTICSEARCH_URL`、`REDIS_URL`、`MOCK_CORE_BASE_URL`。继续使用原机 `STRICT_ANSWER_CHECKS` 和语料索引配置，故障注入关闭。确认 Ollama（4,096 token 上下文）和主 Compose 栈已正常运行。封存命令只测 LangGraph，用不到 `DIFY_API_KEY`。
3. 确认 `../.cache/copilot-dev/author-calibration-paired.jsonl` 是原按 ID 配对的 20 条开发校准记录。一致 16/20，低于 85% 门槛，因此这次复用校准摘要，不传 `--judge-command`。正式规程回答通过率和离线可采纳率仍为未测。运行目录里的逐题报告不作为交接件。

### 东京时间 2026-11-20 当日命令

原机账本已记 ¥11.79725818。作者允许**仅当天**临时使用 ¥20 上限，名义剩余 ¥8.20274182。下面的两个命令用进程环境覆盖，持续使用同一个 `.cache/budget/`，配置文件不需要改。API 上限 ¥20，回放进程提前到 ¥19.40 停止启动下一条请求，为末条用量留 ¥0.60。账本是在模型调用前检查、调用后追加金额，运行期间请停掉其他付费调用，并在东京午夜前结束临时 API。如果已经换日，直接使用本节后面默认上限的办法。

终端一，从仓库根目录进入 `backend/` 后启动冻结版 API。使用独立端口 18083，避免打到已有开发服务；临时关闭可选 Langfuse 云端追踪。

```bash
cd backend
test "$(TZ=Asia/Tokyo date +%F)" = 2026-11-20 && \
  TZ=Asia/Tokyo DAILY_BUDGET_CNY=20 UV_NO_CONFIG=1 PREWARM=true \
  LANGFUSE_PUBLIC_KEY='' LANGFUSE_SECRET_KEY='' \
  uv run --locked uvicorn app.api.main:create_app --factory \
    --host 127.0.0.1 --port 18083
```

终端二，从仓库根目录进入 `backend/` 后，将两个占位符填成**仓库外**的绝对路径。输出目录为新建的一次性运行目录，程序会创建它。

```bash
cd backend
SEALED_CASES='/绝对路径/封存输入.jsonl'
SEALED_RUN_DIR='/绝对路径/封存运行目录'
test "$(TZ=Asia/Tokyo date +%F)" = 2026-11-20 && \
  curl --fail --silent --show-error http://127.0.0.1:18083/health && \
  TZ=Asia/Tokyo DAILY_BUDGET_CNY=19.40 UV_NO_CONFIG=1 \
  uv run --locked python -m scripts.evaluate_copilot \
    --port 18083 --commit fdd5a5eb16e9fb1e7a4e10e9fba9f7e6881cb4c0 \
    --sealed-test "$SEALED_CASES" --run-dir "$SEALED_RUN_DIR" \
    --calibration ../.cache/copilot-dev/author-calibration-paired.jsonl
```

- 这里的 `PREWARM=true` 预建应用服务，客户端没有额外付费预热请求。运行中断时，用同一输入、输出目录、提交和配置，在第二个命令末尾加 `--resume`。已落盘的题档观测会复用。若遇限流，先等至少一分钟再接续；达到预留预算时，转到下一天继续。
- 换日后从两个命令删去日期 `test`（终端二保留 `curl`），API 删去 `DAILY_BUDGET_CNY=20` 使用默认 ¥10，回放将 `DAILY_BUDGET_CNY=19.40` 改成 `DAILY_BUDGET_CNY=9.40` 预留同样余量。原机跑完后按 `Ctrl+C` 停掉终端一的临时 API，再用下面的命令核对默认值和当天累计。终端命令里的覆盖随进程退出结束。

```bash
TZ=Asia/Tokyo UV_NO_CONFIG=1 uv run --locked python - <<'PY'
from app.core.config import CACHE_DIR, get_settings
from app.providers.budget import BudgetLedger

limit = get_settings().daily_budget_cny
ledger = BudgetLedger(CACHE_DIR / "budget", limit)
print(f"默认上限 ¥{limit:.2f}，当日累计 ¥{ledger.spent():.8f}")
PY
```

### 预计调用和费用

若有约 20 道单轮规程题，S/L 各跑一次，共约 40 个最终 SSE 请求。多轮题的每个历史轮也要在对应档重放。一般路径每个请求约有一次本机小模型分类，追问可能另做改写，进入生成时通常有一次付费 DeepSeek 调用。无历史、无重试的 20 道题按最多约 40 次常规生成规划，固定转介、直接回应等路径可以少于这个数。评审模型调用为 0。用 `fdd5a5e` 的规程开发均值估算，每题两档约 ¥0.047063，20 道约 **¥0.94**。这是按实测均值的计划估算，实际预算以当天账本为准。

### 发回哪些结果

完成后发回 `$SEALED_RUN_DIR/report.md` 的聚合内容。报告包含运行条件、校准、技术指标、置信区间、S/L 配对和按类别统计的错误。若只粘贴摘要，保留 `运行条件`、`评审校准`、`技术指标`、`S 与 L 档规程召回对照` 和 `未测的业务指标` 等相关段落，并补东京日期、结束时的当日账本、本次实际增量、是否在中断后续跑，以及上限恢复至 ¥10 的确认。项目日志收到汇总后再记实际花费。`observations.jsonl`、`rows.jsonl`、题目和逐题回答由作者在仓库外保留。
