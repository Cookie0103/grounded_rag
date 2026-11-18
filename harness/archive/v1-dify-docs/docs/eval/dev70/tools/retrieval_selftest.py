import argparse,asyncio,hashlib,json,sys,time
from datetime import datetime
from pathlib import Path
root=next(p for p in Path(__file__).resolve().parents if (p/'backend/app').is_dir() and (p/'AGENTS.md').is_file());sys.path.insert(0,str(root/'backend'))
from app.core.config import get_settings
from app.db.engine import create_engine
from app.retrieval.factory import build_retriever
parser=argparse.ArgumentParser(description='原题单次检索，不传edition、不分解，不运行回答或评审。')
parser.add_argument('--device')
parser.add_argument('--questions',type=Path,default=root/'docs/eval/dev70/questions.jsonl')
parser.add_argument('--evidence',type=Path,default=root/'docs/eval/dev70/evidence.json')
parser.add_argument('--output',type=Path,default=root/'docs/eval/dev70/retrieval-selftest.jsonl')
args=parser.parse_args();out=args.output;out.parent.mkdir(parents=True,exist_ok=True)
async def run():
 original=get_settings();s=original.model_copy(update={'embed_device':args.device or original.embed_device,'embed_batch_size':4})
 engine=create_engine(s)
 qs=[json.loads(v) for v in args.questions.read_text().splitlines() if v.strip()]
 evidence={v['question_id']:v for v in json.loads(args.evidence.read_text())['questions']}
 previous=[]
 if out.exists():previous=[json.loads(v) for v in out.read_text().splitlines() if v.strip()]
 completed={(v['id'],v['question_sha256']) for v in previous if v.get('status')=='ok' and v.get('device')==s.embed_device and v.get('embedding_model')==s.embedding_model and v.get('reranker_model')==s.reranker_model}
 try:
  retriever=await build_retriever(engine,s)
  for q in qs:
   h=hashlib.sha256(q['question'].encode()).hexdigest()
   if (q['id'],h) in completed:continue
   start=time.monotonic()
   result=await asyncio.wait_for(retriever.retrieve(q['question']),timeout=300)
   docs=[v.chunk.document_id for v in result.candidates]
   groups=evidence[q['id']].get('gold_doc_groups',[[v] for v in q['gold_docs']])
   hits=[bool(set(g)&set(docs)) for g in groups]
   record={'id':q['id'],'status':'ok','question':q['question'],'question_sha256':h,'query_mode':'original_question_single_call','edition_filter':None,'decomposition':False,'device':s.embed_device,'embedding_model':s.embedding_model,'reranker_model':s.reranker_model,'degraded':result.degraded,'gold_doc_groups':groups,'group_hits_at_5':hits,'all_required_groups_hit_at_5':all(hits) if hits else None,'top_5':[{'rank':v.rank,'document_id':v.chunk.document_id,'chunk_id':v.chunk.id,'parent_id':v.chunk.parent_id,'rerank_score':v.rerank_score} for v in result.candidates],'timings_ms':result.timings_ms,'wall_seconds':round(time.monotonic()-start,3),'run_at_local':datetime.now().astimezone().isoformat()}
   with out.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
   print(json.dumps({'id':q['id'],'hit':record['all_required_groups_hit_at_5'],'seconds':record['wall_seconds']},ensure_ascii=False),flush=True)
 finally:await engine.dispose()
asyncio.run(run())
