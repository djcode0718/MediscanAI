# MediScanAI — Master Git Documentation Forensic Classification

**Document:** `deployment/GIT_DOCUMENTATION_CLASSIFICATION.md`  
**Date:** 2026-11-16  
**Auditor:** Principal Software Engineer, Git Repository Maintainer & Documentation Architect  
**Branch:** `feature/cloud-docker-deployment` (HEAD: `fc5ad47`)  
**Scope:** Complete forensic audit and classification of all 247 repository Markdown documents  

---

## 1. Classification Methodology & Status Legend

Every Markdown document across the repository has been inspected, categorized, and assigned one of five formal classifications:

- **Class A (ESSENTIAL):** Canonical project, architecture, API, testing, deployment, and operational documentation that **must remain tracked in Git on GitHub**.
- **Class B (IMPORTANT):** Important technical specifications or guidelines that are consolidated into canonical parent documents.
- **Class C (INTERNAL AUDIT):** Useful historical evidence, validation reports, calibration runs, and forensic assessments that **must remain preserved 100% intact on the local filesystem** but untracked from Git to prevent repository bloat.
- **Class D (TEMPORARY / EXPERIMENT LOG):** Intermediate diagnostic dumps, benchmark execution logs, and cache quarantine records preserved locally.
- **Class E (OBSOLETE / DUPLICATE):** Superseded scratch notes or dummy files preserved locally in quarantine.

---

## 2. Master Document Inventory & Classification

```
+-----+------------------------------------------------------------------------------------------+---------+--------------------+---------------------------------------------------------------+
| #   | File Path                                                                                | Tracked | Classification     | Role & Disposition                                            |
+-----+------------------------------------------------------------------------------------------+---------+--------------------+---------------------------------------------------------------+
| 1   | README.md                                                                                | Yes     | **Class A**        | Primary GitHub landing page, quickstart & feature overview    |
| 2   | frontend/README.md                                                                       | Yes     | **Class A**        | Frontend architecture, Vite build & component docs            |
| 3   | evaluation/benchmark/README.md                                                           | Yes     | **Class A**        | Medical diagnostic benchmark overview & dataset structure     |
| 4   | evaluation/benchmark/metric_contract.md                                                  | Yes     | **Class A**        | Evaluation metric definitions, thresholds & scoring bounds    |
| 5   | evaluation/benchmark/judgment_guidelines.md                                              | Yes     | **Class A**        | Clinical judgment guidelines & ground-truth validation rules   |
| 6   | evaluation/e2e/dataset/README.md                                                         | Yes     | **Class A**        | Clinical case dataset specifications & stratification schema  |
| 7   | evaluation/e2e/PROMPT_INVENTORY.md                                                       | Yes     | **Class A**        | Master inventory of clinical system prompts (v1 through v7)   |
| 8   | evaluation/e2e/tools/ADJUDICATION_RUBRIC.md                                              | Yes     | **Class A**        | Diagnostic adjudication rubric & scoring criteria             |
| 9   | evaluation/e2e/audit/methodology_redesign/MEDISCANAI_EVALUATOR_METHODOLOGY.md              | Yes     | **Class A**        | Evaluator methodology, statistical power & judging protocol   |
| 10  | evaluation/retrieval/README.md                                                           | Yes     | **Class A**        | Hybrid retrieval architecture (FAISS + BM25 + CrossEncoder)   |
| 11  | evaluation/retrieval/phase_1_2_b_emergency_guardrail/guardrail_design.md                   | Yes     | **Class A**        | Clinical emergency triage guardrail architecture              |
| 12  | deployment/ARCHITECTURE.md                                                               | Staged  | **Class A**        | Production container stack architecture, networks & data flows|
| 13  | deployment/AUDIT_REPORT.md                                                               | Staged  | **Class A**        | Master Phase 1 infrastructure, dependency & security audit     |
| 14  | deployment/CHANGELOG.md                                                                  | Staged  | **Class A**        | Master deployment changelog across all phases                 |
| 15  | deployment/CHANGE_REVIEW_REPORT.md                                                       | Staged  | **Class A**        | Comprehensive read-only review of 22 pending changes          |
| 16  | deployment/DEPENDENCY_COMPATIBILITY.md                                                   | Staged  | **Class A**        | ARM64 / manylinux wheel compatibility & dependency matrix     |
| 17  | deployment/DEPLOYMENT_DECISIONS.md                                                       | Staged  | **Class A**        | Master Architectural Decision Records (ADR 001 - ADR 008)      |
| 18  | deployment/DEPLOYMENT_SUMMARY.md                                                         | Staged  | **Class A**        | Deployment executive summary & resource requirements          |
| 19  | deployment/FINAL_PRE_PROVISIONING_AUDIT.md                                               | Staged  | **Class A**        | Pre-cloud provisioning readiness & configuration audit         |
| 20  | deployment/FINAL_PROMOTION_GATE_REPORT.md                                                 | Staged  | **Class A**        | Production promotion gate SRE report & OpenMP validation       |
| 21  | deployment/P2_DOCKER_STORAGE_AUDIT.md                                                     | Staged  | **Class A**        | Docker forensic storage audit & P0 cleanup reconciliation      |
| 22  | deployment/P2_FULL_REGRESSION_REPORT.md                                                   | Staged  | **Class A**        | Full regression validation report across 3 consecutive runs    |
| 23  | deployment/P2_MAC_MEMORY_AUDIT.md                                                         | Staged  | **Class A**        | Mac host memory profiling & Docker Desktop VM tuning          |
| 24  | deployment/P2_ML_RUNTIME_RELIABILITY_AUDIT.md                                             | Staged  | **Class A**        | OpenMP thread safety, dynamic linker maps & LCNet stability    |
| 25  | deployment/P2_NEO4J_RESIDUAL_DEPENDENCY_AUDIT.md                                          | Staged  | **Class A**        | Neo4j dormant dependency audit & package retention rationale  |
| 26  | deployment/P2_PRODUCTION_PROMOTION_RECOMMENDATION.md                                      | Staged  | **Class A**        | Production promotion runbook & empirical rollback benchmark    |
| 27  | deployment/PRODUCTION_VERIFICATION.md                                                     | Staged  | **Class A**        | Production runtime verification protocol & live curl suites    |
| 28  | deployment/RUNBOOK.md                                                                    | Staged  | **Class A**        | Production operations runbook, security hardening & recovery   |
| 29  | deployment/TASKS.md                                                                      | Staged  | **Class A**        | Master deployment task tracker (Phase 1, 2, 3)                 |
| 30  | deployment/TEST_MATRIX.md                                                                | Staged  | **Class A**        | Comprehensive test matrix across unit, API, integration suites |
| 31  | deployment/GIT_DOCUMENTATION_CLASSIFICATION.md                                            | Staged  | **Class A**        | Master documentation forensic classification (this document)   |
| 32  | deployment/PROPOSED_GIT_DOCUMENTATION_STRUCTURE.md                                        | Staged  | **Class A**        | Canonical Git documentation structure & maintenance policy     |
| 33  | GIT_PRE_MERGE_AUDIT.md                                                                   | Local   | **Class C**        | Historical pre-merge git status audit (retained locally)       |
| 34  | README-dummy.md                                                                          | Local   | **Class E**        | Obsolete scratch file (retained locally, ignored)              |
| 35  | p4_report.md                                                                             | Untrack | **Class C**        | Phase 4 answer-grounding delivery report (retained locally)    |
| 36  | results/p4/entity_gate_dryrun.md                                                         | Untrack | **Class D**        | Phase 4 entity gate dry-run execution log (retained locally)   |
| 37  | results/p4/symptom_hygiene_audit.md                                                      | Untrack | **Class D**        | Phase 4 symptom hygiene audit log (retained locally)           |
| 38  | deployment/assessment/SYSTEM_INVENTORY.md                                                | Local   | **Class C**        | Phase 0 system component inventory (retained locally)          |
| 39  | deployment/assessment/INFRASTRUCTURE_REQUIREMENTS.md                                     | Local   | **Class C**        | Phase 0 compute/RAM/storage requirement analysis (local)       |
| 40  | deployment/assessment/WORKLOAD_PROFILE.md                                                | Local   | **Class C**        | Phase 0 workload profiling & resource characterization (local) |
| 41  | deployment/assessment/DOCKER_CLEANUP_PLAN.md                                             | Local   | **Class C**        | Phase 0 Docker resource cleanup plan (retained locally)        |
| 42  | deployment/assessment/CPU_IMAGE_TEST_REPORT.md                                           | Local   | **Class C**        | Phase 0 CPU image validation test report (retained locally)    |
| 43  | deployment/assessment/CPU_IMAGE_BUILD_REPORT.md                                          | Local   | **Class C**        | Phase 0 CPU image build layers & packaging report (local)      |
| 44  | deployment/assessment/CPU_IMAGE_DEPENDENCY_COMPATIBILITY.md                              | Local   | **Class C**        | Phase 0 PyPI CPU wheel dependency matrix (retained locally)    |
| 45  | deployment/assessment/MEMORY_AND_STORAGE.md                                              | Local   | **Class C**        | Phase 0 host vs container memory breakdown (retained locally)  |
| 46  | deployment/assessment/CONCURRENCY_AND_CAPACITY.md                                        | Local   | **Class C**        | Phase 0 concurrency scaling limits & capacity models (local)   |
| 47  | deployment/assessment/PHASE_0_SUMMARY.md                                                 | Local   | **Class C**        | Phase 0 executive assessment summary (retained locally)        |
| 48  | deployment/assessment/P0_CLEANUP_EXECUTION_REPORT.md                                     | Local   | **Class C**        | Phase 0 cleanup execution telemetry (retained locally)         |
| 49  | deployment/assessment/DOCKER_ENVIRONMENT_AUDIT.md                                        | Local   | **Class C**        | Phase 0 initial Docker environment audit (retained locally)    |
| 50  | deployment/assessment/DOCKER_IMAGE_LAYER_ANALYSIS.md                                     | Local   | **Class C**        | Phase 0 11.7 GB image layer breakdown (retained locally)       |
| 51  | deployment/assessment/CPU_IMAGE_PERFORMANCE_COMPARISON.md                                | Local   | **Class C**        | Phase 0 CPU vs GPU performance benchmarks (retained locally)   |
| 52  | deployment/assessment/PERFORMANCE_BASELINE.md                                            | Local   | **Class C**        | Phase 0 latency and throughput baseline (retained locally)     |
| 53+ | evaluation/benchmark/candidate_judgments_audit_* (3 files)                              | Untrack | **Class C**        | Historical candidate judgment audits (retained locally)        |
| 56+ | evaluation/benchmark/evidence_adjudication/* (4 files)                                   | Untrack | **Class C**        | Historical evidence adjudication reports (retained locally)    |
| 60+ | evaluation/benchmark/human_review/* (4 files)                                           | Untrack | **Class C**        | Historical human review protocols & guidelines (local)         |
| 64+ | evaluation/benchmark/narrative_references/* (5 files)                                   | Untrack | **Class C**        | Historical narrative reference audits (retained locally)       |
| 69+ | evaluation/benchmark/research_adjudication/* (7 files)                                   | Untrack | **Class C**        | Historical research adjudication logs (retained locally)       |
| 76+ | evaluation/model_pilot/phase_c_2/* (5 files)                                             | Untrack | **Class C**        | Historical model pilot evaluations (retained locally)          |
| 81+ | evaluation/ragas/phase_c_3/* (3 files)                                                   | Untrack | **Class C**        | Historical RAGAS phase C.3 setup & contracts (local)           |
| 84+ | evaluation/ragas/phase_c_4/* (4 files)                                                   | Untrack | **Class C**        | Historical RAGAS phase C.4 audits & failure logs (local)       |
| 88+ | evaluation/ragas/phase_c_5/* (8 files)                                                   | Untrack | **Class C**        | Historical RAGAS phase C.5 evaluation reports (local)          |
| 96+ | evaluation/retrieval/phase_1_1* through phase_f_5* (71 files)                             | Untrack | **Class C**        | Historical retrieval experiment phases & audits (local)        |
|167+ | evaluation/e2e/results/* (23 files)                                                      | Untrack | **Class D**        | Historical evaluation run reports (A3 through A8, B0) (local)  |
|190+ | evaluation/e2e/audit/* (46 files)                                                        | Untrack | **Class C**        | Evaluator calibration plans, audits & dossiers (local)        |
|236+ | evaluation/results/* (11 files)                                                          | Local   | **Class D**        | Automated evaluation run outputs & logs (retained locally)     |
+-----+------------------------------------------------------------------------------------------+---------+--------------------+---------------------------------------------------------------+
```

---

## 3. Summary of Document Counts

- **Total Tracked Markdown Files Before Rationalization:** `154`
- **Total Tracked Markdown Files Proposed After Rationalization:** `32` (Target: 25–30, limit 40)
- **Total Historical / Audit Markdown Files Preserved Locally:** `215` (100% intact on disk)
- **Total Markdown Files on Local Filesystem:** `247` (excluding `node_modules`)
- **Zero documentation deleted.**
