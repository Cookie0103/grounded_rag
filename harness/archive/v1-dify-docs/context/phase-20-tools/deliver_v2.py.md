# deliver_v2.py 源码审查副本

运行版位于仓库外新版迁移包；此处仅供审查。

```python
"""只整理两版缓存；不调用评审、系统或检索。"""
import hashlib,json,sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
ART=Path(__file__).resolve().parent
OLD=ART.parent/'eval-final-20261020'
sys.path.insert(0,str(ROOT/'backend'))
from eval.dataset import load_questions
from eval.evaluate import load_verdicts
from eval.runner import load_cache
from eval.scoring import ScoredQuestion,score_question,summarize

TEST_Q=ART.parent/'test30-review-2026-10-20/questions.jsonl'
SUITES={
    'dev70':(ART.parent/'repo-cache/eval/runs/final-dev70/full',ROOT/'.cache/eval/runs/final-dev70-v2-resumed/full',ART.parent/'eval-inputs/dev70/questions.jsonl'),
    'reg20':(ART.parent/'repo-cache/eval/runs/final-reg20/full',ROOT/'.cache/eval/runs/final-reg20-v2/full',ART.parent/'eval-inputs/dev20/questions.jsonl'),
    'test30':(OLD/'test-storage/eval/runs/final-test30/full',ART/'test30/full',TEST_Q),
}

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def scored(qs,verdicts):return [ScoredQuestion(q,verdicts[q.id],score_question(q,verdicts[q.id])) for q in qs if q.id in verdicts]

def load_run(suite,paths):
    source,out,qpath=paths
    if not (out/'metrics.json').exists():return None
    metrics=read(out/'metrics.json')
    if metrics['not_reviewed']!=0 or metrics['error_questions']!=0 or metrics['judged']!=metrics['planned']:return None
    qs=load_questions(qpath)
    answers=load_cache(source/'answers.jsonl')
    before=load_verdicts(source/'verdicts.jsonl');after=load_verdicts(out/'verdicts.jsonl')
    return {'suite':suite,'source':source,'out':out,'qs':qs,'answers':answers,'before':before,'after':after,'metrics':metrics}

def comparison(runs):
    lines=['# v1与v2并列对照','', '**v2为评审改动后的初步结果，校准通过前不是正式数字。**','','同一批缓存回答和检索资料，只改变评审模板/输入；不重跑系统、不重新检索。评分函数未改，95%区间沿用原bootstrap。严格/宽松指标以成功评审的可回答题为分母，可信得分以成功评审的全部题为分母；原规则的未作答0分保留。','','| 题集 | 版本 | 计划 | 评审完成 | 出错 | 严格成功率 | 宽松正确率（含部分） | 可信得分（95%区间） |','|---|---|---|---|---|---|---|---|---|']
    summaries=[];retrieval_notes=[]
    for r in runs:
        for version,key in [('v1','before'),('v2','after')]:
            s=summarize(scored(r['qs'],r[key]))
            errors=0 if version=='v1' else r['metrics']['error_questions']
            lines.append(f"| {r['suite']} | {version} | {len(r['qs'])} | {s.count} | {errors} | {s.strict_success:.1%} | {s.accuracy:.1%} | {s.trust:+.3f} [{s.ci_low:+.3f}, {s.ci_high:+.3f}] |")
            summaries.append({'suite':r['suite'],'version':version,'planned':len(r['qs']),'judged':s.count,'errors':errors,**asdict(s)})
        retrieval_notes.append(f"{r['suite']}的Recall@5沿用相同缓存与等价来源口径：{r['metrics']['retrieval']['recall_at_5']:.1%}（{r['metrics']['retrieval']['questions']}道可回答题）。")
    lines.extend(['',*retrieval_notes])
    lines.extend(['', '## 历史错误与解释边界', '', 'v2同时包含作者批准的contradiction与support解释变更，不能把全部分差归因于contexts。各套flips.md另列全部nuggets标签变化。', ''])
    for r in runs:
        hp=r['out']/'errors-history.json'
        history=read(hp) if hp.exists() else {}
        lines.append(f"{r['suite']}：历史出错{len(history)}题；当前错误数与历史数分开，不以补评成功删除错误。")
        for qid,messages in history.items():lines.append(f'- {qid}：'+json.dumps(messages,ensure_ascii=False))
    lines.extend(['','## 三套v2报告',''])
    for r in runs:lines.append(f'- [{r["suite"]}报告](<{(r["out"]/"report.md").as_posix()}>)；[完整标签变化](<{(r["out"]/"flips.md").as_posix()}>)')
    lines.extend(['','[新20条校准样本](calibration-sample-v2.md)；[全量翻转](flips.md)；[true→false原回答核对](flips-spot-check.md)。','', 'v1历史文件保持原样。测试30的所有新产物在仓库外；其题集由开发agent参与编写，不是开发者未见的盲测。v2模板仅依据开发/回归校准分歧冻结，未按测试结果修改。CLI默认模型未覆盖；当前未取得可核验的模型ID，不推测型号。'])
    (ART/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    write(ART/'comparison.json',summaries)

def flip_outputs(runs):
    changed=[];all_lines=['# 三套完整v1→v2标签变化','','逐题全列，不抽样、不添加判断；三套仍分开。','']
    spot=['# contradiction true→false：全部原回答核对','', '**以下变化不是“v2判对”的结论；请人工核对是否放过真正编造。** 只转录原回答、两版标签与原规则分数，人工栏留空。','']
    for r in runs:
        all_lines.extend([f'## {r["suite"]}', '',(r['out']/'flips.md').read_text(encoding='utf-8'),''])
        for q in r['qs']:
            if q.id not in r['after']:continue
            a=r['before'][q.id];b=r['after'][q.id]
            if a==b:continue
            direction='true→false' if a.contradiction and not b.contradiction else ('false→true' if not a.contradiction and b.contradiction else 'other')
            row={'suite':r['suite'],'question_id':q.id,'direction':direction,'v1':asdict(a),'v2':asdict(b),'score_v1':score_question(q,a).points,'score_v2':score_question(q,b).points}
            changed.append(row)
            if direction!='true→false':continue
            answer=r['answers'][q.id]
            spot.extend([f'## {r["suite"]} / {q.id}','',q.question,'',f"v1：`{json.dumps(asdict(a),ensure_ascii=False)}`",'',f"v2：`{json.dumps(asdict(b),ensure_ascii=False)}`",'',f"分数：{row['score_v1']:+g} → {row['score_v2']:+g}",'','### 系统原回答','',answer.answer or '（空）','',f"金标文档ID：{', '.join(q.gold_docs) or '无'}",'',f"缓存返回文档ID：{', '.join(answer.retrieved_docs) or '无'}",'',f"原始资料位置：`{r['source']/ 'answers.jsonl'}`（按question_id查找contexts）。",'','人工核对 / 是否存在无依据说法：________________',''])
    counts={r['suite']:dict(Counter(x['direction'] for x in changed if x['suite']==r['suite'])) for r in runs}
    all_lines.insert(4,'各套变化数量：`'+json.dumps(counts,ensure_ascii=False)+'`\n')
    spot.insert(4,f"共{sum(x['direction']=='true→false' for x in changed)}题，包含全部true→false变化。\n")
    (ART/'flips.md').write_text('\n'.join(all_lines),encoding='utf-8')
    if len(runs)==3 and not (ART/'flips-spot-check.md').exists():
        (ART/'flips-spot-check.md').write_text('\n'.join(spot),encoding='utf-8')
    write(ART/'flips.json',changed)
    return changed

def calibration(runs):
    if not all(any(r['suite']==s for r in runs) for s in ['dev70','reg20']):return False
    path=ART/'calibration-sample-v2.md'
    if path.exists():return True
    plan=read(ART/'calibration-plan-v2.json')
    qs={q.id:q for r in runs if r['suite']!='test30' for q in r['qs']}
    answers={key:value for r in runs if r['suite']!='test30' for key,value in r['answers'].items()}
    verdicts={key:value for r in runs if r['suite']!='test30' for key,value in r['after'].items()}
    lines=['# Claude v2评审人工校准样本（待人工标注）','',f"固定随机种子：{plan['seed']}；{plan['method']}。只来自开发/回归，不含测试。",'',f"预期类别分布：{dict(Counter(plan['categories'].values()))}",'','以下仅转录冻结题目、必答点、系统缓存原回答和v2标签；执行agent不加判断。support / partial_support / not_support分别为完整 / 部分 / 不支持。人工栏留空；v2尚未通过校准。','']
    for number,qid in enumerate(plan['question_ids'],1):
        q=qs[qid];v=verdicts[qid]
        lines.extend([f'## {number}. {qid}','',f"预期类别：{plan['categories'][qid]}；题集类别：{q.unanswerable_category or q.type}",'',q.question,'','### 必答点与v2标签','','| 序号 | 重要性 | 题集要点 | v2标签 | 人工标签（留空） |','|---|---|---|---|---|'])
        for i,(n,label) in enumerate(zip(q.nuggets,v.nuggets,strict=True),1):
            lines.append(f'| {i} | {n.importance} | {n.text.replace(chr(10),"<br>").replace("|","\\|")} | {label} | |')
        if not q.nuggets:lines.extend(['','本题无逐点要点，沿用边界行为判定。'])
        lines.extend(['','### 系统原回答','',answers[qid].answer or '（空）','','### v2行为标签','',f'- behavior：`{v.behavior}`',f'- contradiction：`{str(v.contradiction).lower()}`',f'- corrects_premise：`{str(v.corrects_premise).lower()}`',f'- covers_interpretations：`{str(v.covers_interpretations).lower()}`','','人工行为标签 / 备注：________________',''])
    path.write_text('\n'.join(lines),encoding='utf-8')
    return True

if __name__=='__main__':
    runs=[r for suite,paths in SUITES.items() if (r:=load_run(suite,paths)) is not None]
    comparison(runs)
    flips=flip_outputs(runs)
    ready=calibration(runs)
    print(json.dumps({'complete_suites':[r['suite'] for r in runs],'calibration_ready':ready,'flips':{r['suite']:dict(Counter(x['direction'] for x in flips if x['suite']==r['suite'])) for r in runs}},ensure_ascii=False))

```
