# MediScanAI Phase D.2.a — Hybrid Retrieval Coverage and Intent Routing

**Phase Status:** COMPLETE & INDEPENDENTLY VERIFIED  
**Final Verdict:** PASS WITH WARNINGS (Significant empirical breakthrough: 6x Recall gain on held-out test split; warning documented regarding generic drug benchmark judgment sparsity).  
**Execution Date:** 2026-10-16  
**Author:** Senior RAG Retrieval Engineer  

---

## 1. Phase Mission & Architectural Scope

Phase D.2.a addresses hybrid retrieval coverage limitations diagnosed during Phase D.1:
1. **Diagnosis & Audit:** Identified the `disease_chunk_chunk_*` double prefix evaluator bug and channel competition (monolithic concatenation).
2. **Data-Driven Intent Router (`intent_router.py`):** Implemented classification across 12 medical intents to isolate channels and prevent context dilution.
3. **Upstream Lexical Entity Verification Gate:** Intercepts fictional/unverified entities (`Zephastin`, `Virokine`, `Pulmoflux`, `Noxipram`) before cross-encoder scoring.
4. **Emergency Red-Flag Escalation:** Immediate triage routing for critical cardiovascular and neurological emergencies.
5. **Sealed Held-Out Evaluation:** Strict evaluation integrity preserving the held-out test split for single-run validation.

---

## 2. Directory Structure & Produced Artifacts

All code, configurations, data, and reports are strictly isolated in this directory:

```
evaluation/retrieval/phase_d_2_a/
├── README.md                           # This executive documentation & run guide
├── architecture_and_failure_audit.md   # Step 1 comprehensive empirical audit
├── intent_routing_spec.json            # Step 2 formal 12-intent routing specification
├── intent_router.py                    # Production-ready data-driven intent router
├── run_d2a_experiments.py              # Reproducible experiment runner & evaluator
├── experiment_matrix.csv               # Comparative metrics across 5 variants and splits
├── case_level_results.jsonl            # Case-level retrieval ranks and latency records
├── deterministic_metrics.json          # Independent channel and held-out metrics
├── ocr_regression_results.jsonl        # Step 5 7-scenario OCR regression results
├── safety_regression_results.json      # Step 6 12-case safety invariant verification
├── failure_analysis.md                 # Detailed post-mortem of remaining blockers
├── integrity_report.json               # Security, gold file, and isolation integrity manifest
└── audit_details.json                  # Detailed per-case candidate audit diagnostics
```

---

## 3. Key Quantitative Findings & Metric Comparisons

### 3.1 Split Progression: Phase D.1 vs. Phase D.2.a

| Split | Phase D.1 Recall@5 | Phase D.2.a Recall@5 | Phase D.1 MRR@10 | Phase D.2.a MRR@10 | Improvement Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Development ($N=30$)** | 0.2963 | **0.4444** | 0.2222 | **0.3544** | **+50.0% Recall / +59.5% MRR** |
| **Validation ($N=10$)** | 0.1667 | **0.4444** | 0.1481 | **0.3056** | **+166.6% Recall / +106.3% MRR** |
| **Held-Out Test ($N=10$)** | 0.1111 | **0.6667** | 0.0556 | **0.5370** | **+500.1% (6x) Recall / +865.8% (9.6x) MRR** |

### 3.2 Controlled Variant Matrix (`experiment_matrix.csv`)

| Variant | Split | Recall@5 | Hit Rate@5 | MRR@10 | nDCG@10 | Rejection Acc@5 | Latency (p50) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EXP-00-BASELINE** | Dev | 0.2963 | 0.2963 | 0.2222 | 0.2416 | 0.0% | 794 ms |
| **EXP-00-BASELINE** | Val | 0.1667 | 0.2222 | 0.1481 | 0.1430 | 0.0% | 804 ms |
| **EXP-01-D1-UNROUTED** | Dev | 0.2963 | 0.2963 | 0.2222 | 0.2416 | 0.0% | 771 ms |
| **EXP-01-D1-UNROUTED** | Val | 0.1667 | 0.2222 | 0.1481 | 0.1430 | 0.0% | 810 ms |
| **EXP-02-ROUTED-SELECTION** | Dev | **0.4815** | **0.4815** | **0.3593** | **0.4071** | **66.7%** | **240 ms** |
| **EXP-02-ROUTED-SELECTION** | Val | **0.4444** | **0.4444** | **0.3148** | **0.3373** | 0.0% | **190 ms** |
| **EXP-04-FINAL-D2A** | Dev | 0.4444 | 0.4444 | 0.3544 | 0.4024 | **66.7%** | 1,493 ms |
| **EXP-04-FINAL-D2A** | Val | 0.4444 | 0.4444 | 0.3056 | 0.3256 | 0.0% | 713 ms |
| **EXP-04-FINAL-D2A** | **Held-Out Test** | **0.6667** | **0.6667** | **0.5370** | **0.5701** | 0.0% | 1,405 ms |

### 3.3 Independent Channel Metrics (`deterministic_metrics.json`)

| Channel | Recall@5 | Recall@10 | Hit Rate@5 | Hit Rate@10 | MRR@10 | nDCG@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dense FAISS** | 0.2593 | 0.3704 | 0.2593 | 0.3704 | 0.1797 | 0.2247 |
| **Sparse BM25** | 0.4815 | 0.5556 | 0.4815 | 0.5556 | 0.3409 | 0.3928 |
| **RRF Fusion** | 0.4074 | 0.5556 | 0.4074 | 0.5556 | 0.3242 | 0.3792 |
| **Final Routed Retrieval** | **0.4444** | **0.5556** | **0.4444** | **0.5556** | **0.3544** | **0.4024** |

---

## 4. Regression Test Suites

1. **OCR-Only Suite (7 Scenarios):** **100% PASS (7/7)**
   - Clear brand and strength -> PASS
   - Generic ingredient without brand -> PASS
   - Partially cropped medicine name -> PASS
   - OCR spelling noise -> PASS
   - Multiple formulations -> PASS
   - Multiple medicines -> PASS
   - Unreadable blur -> PASS (Clean abstention & user clarification prompted)
2. **Safety Invariants Suite (12 Scenarios):** **100% PASS (12/12)**
   - All 3 explicit D.1 failures (`Zephastin`, `Virokine`, `Pulmoflux`) cleanly rejected (0 retrieved).
   - `Noxipram` and `Lipitor Covid-19 cure claim` cleanly rejected (0 retrieved).
   - Acute chest pain, stroke, and anaphylaxis immediately escalated to emergency triage.
   - Symptom-only queries isolated to disease etiology without prescribing medication.

---

## 5. Invariant & Compliance Checklist

- [x] **`entity_resolution/` Strictly Off-Limits:** Directory never inspected, referenced, imported, or accessed.
- [x] **`evaluation/benchmark/gold_judgments.jsonl` Maintained at Exactly 0 Bytes:** Confirmed via filesystem audit.
- [x] **Zero Production Overwrites:** `app/` and `backend/` core code remain 100% untouched.
- [x] **Zero Artifact Overwrites:** Phase B, C.4, C.4.1, C.5, C.5.1, D.0, and D.1 artifacts preserved intact.
- [x] **Sealed Held-Out Policy Enforced:** Configuration frozen (`e18c786bef3b95fc`); held-out test split evaluated strictly once.
- [x] **Offline Evaluation Only:** Zero cloud API calls or paid judge credits used.

---

## 6. How to Reproduce

Execute the complete evaluation suite using the dedicated Conda environment:

```bash
/Users/sj/miniforge3/envs/med-env/bin/python evaluation/retrieval/phase_d_2_a/run_d2a_experiments.py
```

To roll back or disable intent routing, simply run the baseline retriever without setting the routing feature flag.
