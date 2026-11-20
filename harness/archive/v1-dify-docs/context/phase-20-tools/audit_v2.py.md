# audit_v2.py 源码审查副本

运行版位于仓库外新版迁移包；此处仅供审查。

```python
"""交付审计：只读缓存、哈希和文本，不调用模型。"""
import hashlib,json,re,subprocess,sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
ART=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
from deliver_v2 import SUITES,load_run
from scripts.audit_rejudge import audit_run
from scripts.rejudge_artifacts import verify_frozen

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def relocate(raw):
    value=str(raw).replace(chr(92),'/')
    mappings=[
        ('D:/项目/秋招项目/SONY/grounded_rag/.cache/',ART.parent/'repo-cache'),
        ('D:/项目/秋招项目/SONY/grounded_rag/docs/eval/dev70/',ART.parent/'eval-inputs/dev70'),
        ('D:/项目/秋招项目/SONY/grounded_rag/docs/eval/dev20/',ART.parent/'eval-inputs/dev20'),
        ('C:/Users/user/.codex/visualizations/2026/10/20/01a158d1-5d55-7d72-9647-6d2defd22b8e/',ART.parent),
        ('C:/Users/user/.codex/visualizations/2026/10/19/01a1568a-21dc-7481-8249-41632f5557fd/test30-review-2026-10-20/',ART.parent/'test30-review-2026-10-20'),
        ('D:/项目/秋招项目/SONY/grounded_rag/',ROOT),
    ]
    for prefix,target in mappings:
        if value.startswith(prefix):return target/value[len(prefix):]
    return Path(raw)

def matches(paths):return all(hashlib.sha256(relocate(p).read_bytes()).hexdigest()==value for p,value in paths.items())
protected=read(ART.parent/'eval-rejudge-v2-20261020/protected-hashes.json')
frozen=read(ART/'v2-frozen-repair.json')
assert matches(protected),'v1历史结果、评分、业务、题集/evidence或预算发生变化'
verify_frozen(ART/'v2-frozen-repair.json')
checks={'protected_v1_answers_verdicts_reports_unchanged':True,'scoring_business_questions_evidence_budget_unchanged':True,'v2_frozen_files_unchanged':True}
runs=[];expected_flips={};true_false=set()
for suite,paths in SUITES.items():
    r=load_run(suite,paths);assert r is not None
    runs.append(r)
    n=len(r['qs']);out=r['out']
    cache=[json.loads(line) for line in (out/'verdicts.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(cache)==n==len(r['after'])
    assert r['metrics']['judged']==n and r['metrics']['error_questions']==0
    assert not read(out/'errors.json') and not r['metrics']['human_calibrated']
    assert not (out/'answers.jsonl').exists()
    assert (out/'pilot-report.md').is_file()
    manifest=read(out/'manifest.json')
    assert not manifest['system_rerun'] and not manifest['retrieval_rerun']
    assert matches(manifest['sha256'])
    audit_run(out,r['source'],paths[2],ART/'v2-frozen-repair.json')
    for q in r['qs']:
        a=r['before'][q.id];b=r['after'][q.id]
        if a==b:continue
        direction='true→false' if a.contradiction and not b.contradiction else ('false→true' if not a.contradiction and b.contradiction else 'other')
        expected_flips[(suite,q.id)]=direction
        if direction=='true→false':true_false.add((suite,q.id))
        assert q.id in (out/'flips.md').read_text(encoding='utf-8')
    if suite=='test30':
        assert not out.resolve().is_relative_to(ROOT.resolve())
    checks[suite]={'cached_answers':n,'v2_judged':n,'errors':0,'new_system_answers_files':0,'v1_files_unchanged':True}

flips=read(ART/'flips.json')
assert {(x['suite'],x['question_id']):x['direction'] for x in flips}==expected_flips
assert len(flips)==len(expected_flips)
spot_path=ART/'flips-spot-check.md'
assert not spot_path.resolve().is_relative_to(ROOT.resolve())
spot=spot_path.read_text(encoding='utf-8')
spot_ids=set(re.findall(r'^## (dev70|reg20|test30) / ((?:dev|test)\d+)$',spot,re.M))
assert spot_ids==true_false
for r in runs:
    for q in r['qs']:
        if (r['suite'],q.id) in true_false:
            assert r['answers'][q.id].answer in spot
checks['all_label_flips_complete']=len(expected_flips)
checks['contradiction_directions']={suite:dict(Counter(v for (s,q),v in expected_flips.items() if s==suite)) for suite in SUITES}
checks['true_to_false_spot_check_complete']=len(true_false)
plan=read(ART/'calibration-plan-v2.json')
sample=(ART/'calibration-sample-v2.md').read_text(encoding='utf-8')
sample_ids=re.findall(r'^## \d+\. (dev\d+)$',sample,re.M)
assert len(sample_ids)==20 and set(sample_ids)==set(plan['question_ids'])
assert plan['seed']==20261021
assert all(Counter(plan['categories'].values())[name]>=2 for name in ['answerable','refuse','clarify','correct_premise'])
for r in runs:
    if r['suite']=='test30':continue
    for q in r['qs']:
        if q.id in sample_ids:assert q.question in sample and r['answers'][q.id].answer in sample
checks['calibration']={'samples':20,'seed':20261021,'expected_categories':dict(Counter(plan['categories'].values())),'test_items':0,'original_answer_verbatim':True,'human_labels_blank':True}
assert subprocess.run(['git','merge-base','--is-ancestor',frozen['source_git_base'],'HEAD'],cwd=ROOT).returncode==0
assert subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0
checks['git_source_ancestry_verified']=True
checks['no_staged_changes']=True
initial=read(ART.parent/'repo-cache/eval/runs/final-dev70-v2/full/errors.json')
history=read(ROOT/'.cache/eval/runs/final-dev70-v2-resumed/full/errors-history.json')
assert len(initial)==18
assert all(qid in history and message in history[qid] for qid,message in initial.items())
checks['historical_limit_errors_preserved']=18
checks['all_passed']=True
(ART/'audit-v2.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False))

```
