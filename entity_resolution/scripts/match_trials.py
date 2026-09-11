#!/usr/bin/env python3
"""MediScanAI 2.0 — v3.4 trial→FDA resolver.
Adds strength-aware scoring and recovers missing ClinicalTrials intervention IDs
by exact normalized alias/name linkage where the alias key is unique.
"""
from __future__ import annotations
import argparse,gzip,json,multiprocessing as mp,pickle,sys
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm
from normalization import parse_intervention
from candidate_generation import retrieve_candidates
from scoring import evaluate_candidate,classify_match,MatchVerdict
BASE=Path(__file__).resolve().parents[1]; DATA_DIR=BASE/'data'; RESULTS_DIR=BASE/'results'; CHECKPOINT_DIR=BASE/'checkpoints'; INDEX_FILE=DATA_DIR/'indexes'/'fda_name_index.pkl'; TRIAL_INTERVENTIONS_FILE=DATA_DIR/'trial_interventions.jsonl.gz'; TRIAL_ALIASES_FILE=DATA_DIR/'trial_aliases.jsonl.gz'; STATE_FILE=CHECKPOINT_DIR/'state.json'; CHUNK_SIZE=10000; WORKER_INDEX=None

def init_worker(idx):
 global WORKER_INDEX; WORKER_INDEX=idx

def _score(q,index):
 fda=index['fda_records']; scored=[]
 for name in retrieve_candidates(q,index):
  scored.append((name,evaluate_candidate(q,name,index['normalized'][name],index['compact'][name],index['tokens'][name],index['identifiers'][name],index.get('radiolabels',{}).get(name,[]),index['token_idf'],index.get('strength_values',{}).get(name),index.get('bare_strengths',{}).get(name))))
 scored.sort(key=lambda x:x[1]['composite_score'],reverse=True); return classify_match(q,scored,fda)

def _result(row,q,v,alias_info=None):
 feat=dict(v.features or {})
 if alias_info: feat.update(alias_info)
 return {'nct_id':row.get('nct_id',''),'intervention_id':str(row.get('intervention_id','') or ''),'intervention_name':row.get('intervention_name',''),'normalized_name':q.normalized,'status':v.status,'match_method':v.method,'canonical_drug_id':v.canonical_drug_id,'all_canonical_ids':v.all_canonical_ids,'matched_fda_name':v.matched_fda_name,'confidence':v.confidence,'margin':v.margin,'features':feat,'source_file':row.get('source_file','trial_interventions.jsonl.gz')}

def process_single_row(row, aliases_by_id, alias_name_to_ids):
 idx=WORKER_INDEX; raw=row.get('intervention_name',''); q=parse_intervention(raw)
 if q.is_empty or len(q.normalized)<2: return _result(row,q,MatchVerdict('unresolved','too_short',None,[],None,0,0,{}))
 iid=str(row.get('intervention_id','') or '').strip(); recovered=False
 if not iid:
  ids=alias_name_to_ids.get(q.normalized,())
  if len(ids)==1: iid=next(iter(ids)); recovered=True
 v=_score(q,idx)
 # Alias evidence: only for a known/recovered intervention_id; use aliases as independent query variants.
 aliases=aliases_by_id.get(iid,[]) if iid else []
 best_alias=None
 if aliases and v.status in {'resolved_medium','query_ambiguous','unresolved'}:
  for a in aliases[:30]:
   ap=parse_intervention(a)
   if ap.is_empty: continue
   av=_score(ap,idx)
   if av.canonical_drug_id and (best_alias is None or av.confidence>best_alias[0]): best_alias=(av.confidence,av)
  if best_alias:
   ac=best_alias[1]
   if v.canonical_drug_id==ac.canonical_drug_id and v.status=='resolved_medium':
    v.status='resolved_high'; v.method=v.method+'+alias_consensus'; v.confidence=min(1.0,round(v.confidence+.06,4))
   elif not v.canonical_drug_id and ac.status=='resolved_high':
    v=MatchVerdict('resolved_high','alias_rescue',ac.canonical_drug_id,ac.all_canonical_ids,ac.matched_fda_name,ac.confidence,ac.margin,ac.features)
 return _result(row,q,v,{'alias_id_recovered':recovered,'alias_intervention_id':iid,'alias_count':len(aliases),'alias_used':bool(best_alias)})

def worker_task(x):
 batch,byid,byname=x; return [process_single_row(r,byid,byname) for r in batch]

def load_aliases():
 byid=defaultdict(list); byname=defaultdict(set)
 if not TRIAL_ALIASES_FILE.exists(): return {},{}
 with gzip.open(TRIAL_ALIASES_FILE,'rt',encoding='utf-8') as f:
  for line in f:
   if not line.strip(): continue
   r=json.loads(line); iid=str(r.get('intervention_id','') or '').strip(); name=str(r.get('name') or '').strip()
   if iid and name:
    byid[iid].append(name); p=parse_intervention(name); 
    if p.normalized: byname[p.normalized].add(iid)
 print(f'Loaded {len(byid):,} intervention alias groups; {len(byname):,} normalized alias keys.')
 return dict(byid),dict(byname)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int); ap.add_argument('--fresh',action='store_true'); ap.add_argument('--workers',type=int,default=max(1,mp.cpu_count()-1)); args=ap.parse_args(); CHECKPOINT_DIR.mkdir(exist_ok=True); RESULTS_DIR.mkdir(exist_ok=True)
 if not INDEX_FILE.exists(): print('ERROR: build FDA index first.'); sys.exit(1)
 with open(INDEX_FILE,'rb') as f: idx=pickle.load(f)
 aliases_by_id,alias_name_to_ids=load_aliases(); rows=[]
 with gzip.open(TRIAL_INTERVENTIONS_FILE,'rt',encoding='utf-8') as f:
  for line in f:
   if line.strip(): rows.append(json.loads(line))
   if args.limit and len(rows)>=args.limit: break
 total=len(rows); start=0
 if args.fresh:
  for p in CHECKPOINT_DIR.glob('chunk_*.jsonl.gz'): p.unlink()
  if STATE_FILE.exists(): STATE_FILE.unlink()
 elif STATE_FILE.exists(): start=json.loads(STATE_FILE.read_text()).get('completed_chunks',0)
 chunks=(total+CHUNK_SIZE-1)//CHUNK_SIZE; print(f'Processing {total:,} rows in {chunks} chunks with {args.workers} workers.')
 with mp.Pool(args.workers,initializer=init_worker,initargs=(idx,)) as pool:
  for ci in range(start,chunks):
   a=ci*CHUNK_SIZE; b=min(a+CHUNK_SIZE,total); batch=rows[a:b]; sub=max(1,len(batch)//max(args.workers*4,1)); jobs=[(batch[i:i+sub],aliases_by_id,alias_name_to_ids) for i in range(0,len(batch),sub)]
   out=[]
   for r in tqdm(pool.imap(worker_task,jobs),total=len(jobs),desc=f'Chunk {ci+1}/{chunks} [{a:,}..{b:,}]'): out.extend(r)
   fn=CHECKPOINT_DIR/f'chunk_{ci+1:06d}.jsonl.gz'; tmp=CHECKPOINT_DIR/f'.chunk_{ci+1:06d}.tmp'
   with gzip.open(tmp,'wt',encoding='utf-8') as f:
    for r in out: f.write(json.dumps(r,ensure_ascii=False)+'\n')
   tmp.replace(fn); STATE_FILE.write_text(json.dumps({'completed_chunks':ci+1,'total_records':total},indent=2))
 print('Matching complete. Run merge_results.py.')
if __name__=='__main__': main()
