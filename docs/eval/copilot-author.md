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

用开发集完成调优并冻结代码、提示词、语料和评审配置后，由作者本人从 `backend/` 运行下面的命令。`SEALED_CASES` 是作者保管的仓库外封存 JSONL，`SEALED_RUN_DIR` 是仓库外新建的独立运行目录，二者均为作者本机的绝对路径。

```bash
uv run python -m scripts.evaluate_copilot \
  --sealed-test "$SEALED_CASES" --run-dir "$SEALED_RUN_DIR" \
  --judge-command "$REVIEW_COMMAND" \
  --calibration ../.cache/copilot-dev/author-calibration.jsonl
```

如中途退出，用同一命令、同一目录加 `--resume` 接续该次运行。完成后保留开发和封存各自的 `report.md`。交接时只提供运行日期、版本、校准一致数及样本数、聚合指标和区间、按类型计数的错误归因、是否仅运行一次，可供项目记录验收。题目、逐题回答、评审输入和原文留在作者本机。
