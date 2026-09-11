#!/usr/bin/env python3
"""MediScanAI v3.4.1 benchmark: safety, formulation and prefix regressions."""
import pickle,sys
from pathlib import Path
from normalization import parse_intervention
from candidate_generation import retrieve_candidates
from scoring import evaluate_candidate,classify_match

BASE=Path(__file__).resolve().parents[1]
INDEX_FILE=BASE/'data'/'indexes'/'fda_name_index.pkl'

# expected status is intentionally strict only where the benchmark represents a
# safety invariant.  None means "inspect parser/structure, but don't require a
# particular match status".
CASES=[
('0 Hz Control','unresolved'),
('1,2 dithiolane 3 valeric acid','unresolved'),
('#1 Respiratory Care Solution','unresolved'),
('10-10-10 Protocol','unresolved'),
('30 Gy over 3 weeks','unresolved'),
('211 Information Sheet','unresolved'),
('25G x 1 Needle Autoinjector','unresolved'),
('3d printed restoration','unresolved'),
('500 with BP treatment','unresolved'),
('6% HES 130/0.4 in a saline solution','unresolved'),
('7.5% hypertonic saline/6% Dextran-70','unresolved'),
('131-MIBG + Vorinostat','unresolved'),
('177Lu-Dotatate PRRT','unresolved'),

# Wrong formulation strengths must never become a formulation-level match.
('0.5% Bupivacaine HCl','unresolved'),
('0.12% saline','unresolved'),
('25% saline','unresolved'),
('10% dextrose','unresolved'),
('20% dextrose','unresolved'),
('2% benzocaine','unresolved'),
('2% lidocaine gel','unresolved'),
('20% hydrogen peroxide','unresolved'),
('0.04% capsaicin patch','unresolved'),

# Matching strength is allowed. This was previously an incorrect benchmark
# expectation: 0.075% must be compatible with the same 0.075 candidate.
('0.075% capsaicin cream','resolved_high'),

('PF-04995274',None),('0.075 mg NX-1207',None),('JNJ-42491293',None),
('5FU',None),('3TC',None),

# Stereo must survive while ordinary ClinicalTrials list prefixes disappear.
('(+)-Epicatechin',None),('(-)-Epicatechin',None),
('[89Zr]Panitumumab PET-MRI',None),('(+/-) Bupivacaine HCl',None),
('+ Folic acid',None),('-Oxaliplatin 85 mg/m2 IV on Day 1',None),
('-5-FU (Fluorouracil) 2,400 mg/m2 IV over 46-48 hours',None),
]

def verdict(q,index):
    sc=[]
    for n in retrieve_candidates(q,index):
        sc.append((n,evaluate_candidate(
            q,n,index['normalized'][n],index['compact'][n],index['tokens'][n],
            index['identifiers'][n],index.get('radiolabels',{}).get(n,[]),
            index['token_idf'],index.get('strength_values',{}).get(n),
            index.get('bare_strengths',{}).get(n))))
    sc.sort(key=lambda x:x[1]['composite_score'],reverse=True)
    return classify_match(q,sc,index['fda_records'])

def parser_invariants(q,p):
    if q == '(+)-Epicatechin':
        return p.normalized == 'epicatechin' and p.stereochemistry == ['(+)-']
    if q == '(-)-Epicatechin':
        return p.normalized == 'epicatechin' and p.stereochemistry == ['(-)-']
    if q == '(+/-) Bupivacaine HCl':
        return p.normalized == 'bupivacaine hcl' and bool(p.stereochemistry)
    if q == '+ Folic acid':
        return p.normalized == 'folic acid' and not p.stereochemistry
    if q == '-Oxaliplatin 85 mg/m2 IV on Day 1':
        return p.normalized.startswith('oxaliplatin ') and '85 mg/m2' in p.measurements
    if q == '-5-FU (Fluorouracil) 2,400 mg/m2 IV over 46-48 hours':
        return p.normalized.startswith('5-fu fluorouracil') and '2,400 mg/m2' in p.measurements
    return True

def main():
    if not INDEX_FILE.exists():
        print('Build index first.'); sys.exit(1)
    with open(INDEX_FILE,'rb') as f: idx=pickle.load(f)
    failures=0
    for q,expected in CASES:
        p=parse_intervention(q)
        ok=parser_invariants(q,p)
        v=verdict(p,idx)
        if expected and v.status != expected: ok=False
        if expected=='unresolved' and v.status in {'resolved_high','resolved_medium'}: ok=False
        print(f"[{'PASS' if ok else 'FAIL'}] {q!r} -> {v.status}/{v.method}; match={v.matched_fda_name}; strength={v.features.get('strength_status')}; normalized={p.normalized!r}")
        if not ok: failures+=1
    print('\n' + ('ALL v3.4.1 BENCHMARKS PASSED.' if failures==0 else f'BENCHMARK FAILED: {failures}'))
    sys.exit(1 if failures else 0)

if __name__=='__main__': main()
