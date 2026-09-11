#!/usr/bin/env python3
"""MediScanAI 2.0 — v3.4 FDA index builder with precomputed candidate metadata."""
from __future__ import annotations
import gzip,json,math,pickle,time
from collections import Counter,defaultdict
from pathlib import Path
from tqdm import tqdm
from normalization import parse_intervention
ROOT=Path(__file__).resolve().parents[1]; DATA_DIR=ROOT/'data'; INDEX_DIR=DATA_DIR/'indexes'; FDA_FILE=DATA_DIR/'fda_names.jsonl.gz'; INDEX_FILE=INDEX_DIR/'fda_name_index.pkl'; METADATA_FILE=INDEX_DIR/'index_metadata.json'; INDEX_DIR.mkdir(parents=True,exist_ok=True)
def main():
 t=time.time(); print('='*80); print('MEDISCANAI 2.0 — v3.4 FDA INDEX BUILDER'); print('='*80)
 name_to_ids=defaultdict(set); n=0
 with gzip.open(FDA_FILE,'rt',encoding='utf-8') as f:
  for line in tqdm(f,desc='Reading FDA Names',unit='lines'):
   if not line.strip(): continue
   o=json.loads(line); name=str(o.get('normalized_name') or '').strip(); cid=o.get('canonical_drug_id')
   if name and cid: name_to_ids[name].add(cid); n+=1
 names=list(name_to_ids); total=len(names); print(f'Loaded {n:,} records ({total:,} unique names).')
 normalized={}; compact={}; tokens={}; identifiers={}; radios={}; strengths={}; bare={}; exact=defaultdict(list); comp=defaultdict(list); ident=defaultdict(list); tokenidx=defaultdict(set); ngramidx=defaultdict(set); tdf=Counter(); gdf=Counter()
 for name in tqdm(names,desc='Parsing FDA Names'):
  p=parse_intervention(name,candidate_mode=True); normalized[name]=p.normalized; compact[name]=p.compact; tokens[name]=p.tokens; identifiers[name]=p.identifiers; radios[name]=p.radiolabels; strengths[name]=p.strength_values; bare[name]=p.bare_strengths
  if p.normalized: exact[p.normalized].append(name)
  if p.compact: comp[p.compact].append(name)
  for x in p.identifiers: ident[x].append(name)
  for x in p.tokens: tokenidx[x].add(name); tdf[x]+=1
  if len(p.compact)>=3:
   grams={p.compact[i:i+3] for i in range(len(p.compact)-2)}
   for g in grams: ngramidx[g].add(name); gdf[g]+=1
 token_idf={x:math.log((1+total)/(1+d))+1 for x,d in tdf.items()}; ngram_idf={x:math.log((1+total)/(1+d))+1 for x,d in gdf.items()}
 payload={'fda_records':{k:sorted(v) for k,v in name_to_ids.items()},'normalized':normalized,'compact':compact,'tokens':tokens,'identifiers':identifiers,'radiolabels':radios,'strength_values':strengths,'bare_strengths':bare,'exact_index':dict(exact),'compact_index':dict(comp),'identifier_index':dict(ident),'token_index':{k:tuple(v) for k,v in tokenidx.items()},'ngram_index':{k:tuple(v) for k,v in ngramidx.items()},'token_idf':token_idf,'ngram_idf':ngram_idf,'version':'3.4'}
 with open(INDEX_FILE,'wb') as f: pickle.dump(payload,f,pickle.HIGHEST_PROTOCOL)
 meta={'record_count':n,'unique_names':total,'unique_exact_keys':len(exact),'unique_compact_keys':len(comp),'unique_identifiers':len(ident),'unique_tokens':len(tdf),'unique_ngrams':len(gdf),'ambiguous_fda_names':sum(len(v)>1 for v in name_to_ids.values()),'build_timestamp':time.strftime('%Y-%m-%d %H:%M:%S'),'version':'3.4'}
 METADATA_FILE.write_text(json.dumps(meta,indent=2),encoding='utf-8'); print(f'Index created in {time.time()-t:.2f}s; size={INDEX_FILE.stat().st_size/(1024*1024):.2f} MB')
if __name__=='__main__': main()
