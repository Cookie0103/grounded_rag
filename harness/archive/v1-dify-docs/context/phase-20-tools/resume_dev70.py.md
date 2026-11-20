# resume_dev70.py 源码审查副本

运行版位于仓库外新版迁移包；此处仅供审查。

```python
"""新目录续评：仅在作者授权真实评审后执行。"""
import argparse,asyncio,sys
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,required=True)
parser.add_argument('--transfer',type=Path,required=True)
args=parser.parse_args()
root=args.repo.resolve();transfer=args.transfer.resolve()
sys.path.insert(0,str(root/'backend'))
from scripts.rejudge import run_rejudge
from app.core.logging import configure_logging
configure_logging('INFO')
result=asyncio.run(run_rejudge(
    transfer/'repo-cache/eval/runs/final-dev70/full',
    root/'.cache/eval/runs/final-dev70-v2-resumed/full',
    transfer/'eval-inputs/dev70/questions.jsonl',
    seed_run=transfer/'repo-cache/eval/runs/final-dev70-v2/full',
    frozen_path=root/'harness/context/phase-20-v2-repair-freeze.json',
))
if result.judge_errors or result.system_errors:raise SystemExit(1)

```
