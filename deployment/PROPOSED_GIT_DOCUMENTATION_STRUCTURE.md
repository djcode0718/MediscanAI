# MediScanAI — Canonical Git Documentation Architecture & Maintenance Policy

**Document:** `deployment/PROPOSED_GIT_DOCUMENTATION_STRUCTURE.md`  
**Date:** 2026-11-16  
**Auditor:** Principal Software Engineer, Git Repository Maintainer & Documentation Architect  
**Branch:** `feature/cloud-docker-deployment` (HEAD: `fc5ad47`)  

---

## 1. Executive Summary & Architecture Goals

This document specifies the canonical tracked documentation structure for MediScanAI on GitHub.

The objective is to establish a clean, professional, and maintainable repository footprint that:
1. Keeps the tracked Markdown count strictly within the target range of **25–30 files** (absolute limit 40).
2. Provides complete coverage across all 16 required project domains (architecture, installation, APIs, auth, database, ML pipelines, retrieval, speech, OCR, testing, Docker, production operations, recovery, and security).
3. Preserves all 215+ historical evaluation dossiers, experiment runs, and forensic assessments **100% intact on the local filesystem** without cluttering GitHub pull requests or search results.

---

## 2. Canonical Tracked Documentation Structure (Exactly 32 Files)

```
MediScanAI/
├── README.md                                          [1]  Project Overview, Architecture & Quickstart
├── frontend/
│   └── README.md                                      [2]  Frontend React 19 / Vite UI Documentation
│
├── evaluation/
│   ├── benchmark/
│   │   ├── README.md                                  [3]  Evaluation Benchmark Overview
│   │   ├── metric_contract.md                         [4]  Diagnostic Metric Contracts & Scoring Bounds
│   │   └── judgment_guidelines.md                     [5]  Clinical Judgment Guidelines & Ground-Truth Rules
│   ├── e2e/
│   │   ├── dataset/
│   │   │   └── README.md                              [6]  Evaluation Dataset Format & Case Stratification
│   │   ├── audit/
│   │   │   └── methodology_redesign/
│   │   │       └── MEDISCANAI_EVALUATOR_METHODOLOGY.md[7]  Evaluator Methodology, Statistics & Judging
│   │   ├── tools/
│   │   │   └── ADJUDICATION_RUBRIC.md                 [8]  Adjudication Rubric & Scoring Protocol
│   │   └── PROMPT_INVENTORY.md                        [9]  Clinical Prompt Template Catalog (v1 - v7)
│   └── retrieval/
│       ├── README.md                                  [10] Retrieval Engine Architecture & Hybrid Search
│       └── phase_1_2_b_emergency_guardrail/
│           └── guardrail_design.md                    [11] Clinical Emergency Triage Guardrail Design
│
└── deployment/
    ├── ARCHITECTURE.md                                [12] Production Container Topology & Network Security
    ├── AUDIT_REPORT.md                                [13] Phase 1 Master Architecture & Security Audit
    ├── CHANGELOG.md                                   [14] Master Deployment Changelog Across All Phases
    ├── CHANGE_REVIEW_REPORT.md                        [15] Formal Pre-Acceptance 22-Change Review Report
    ├── DEPENDENCY_COMPATIBILITY.md                    [16] Dependency & ARM64 Wheel Compatibility Matrix
    ├── DEPLOYMENT_DECISIONS.md                        [17] Master Architectural Decision Records (ADR 001-008)
    ├── DEPLOYMENT_SUMMARY.md                          [18] Deployment Executive Summary & Sizing
    ├── FINAL_PRE_PROVISIONING_AUDIT.md                [19] Pre-Cloud Provisioning Readiness Audit
    ├── FINAL_PROMOTION_GATE_REPORT.md                 [20] Final Promotion Gate SRE & Reliability Report
    ├── P2_DOCKER_STORAGE_AUDIT.md                     [21] Docker Storage Forensic Audit & P0 Cleanup
    ├── P2_FULL_REGRESSION_REPORT.md                   [22] Full Application Regression Report (3 Runs)
    ├── P2_MAC_MEMORY_AUDIT.md                         [23] Mac Memory Baseline & Docker Desktop Sizing
    ├── P2_ML_RUNTIME_RELIABILITY_AUDIT.md             [24] ML Runtime & OpenMP Thread Safety Audit
    ├── P2_NEO4J_RESIDUAL_DEPENDENCY_AUDIT.md          [25] Neo4j Dormant Dependency Retention Audit
    ├── P2_PRODUCTION_PROMOTION_RECOMMENDATION.md      [26] Production Promotion Runbook & Rollback Guide
    ├── PRODUCTION_VERIFICATION.md                     [27] End-to-End Production Verification Protocol
    ├── RUNBOOK.md                                     [28] Master Cloud Operations & Hardening Runbook
    ├── TASKS.md                                       [29] Master Deployment Task Tracker (P1, P2, P3)
    ├── TEST_MATRIX.md                                 [30] Comprehensive Test Matrix Across All Tiers
    ├── GIT_DOCUMENTATION_CLASSIFICATION.md            [31] Forensic Classification of All 247 MD Files
    └── PROPOSED_GIT_DOCUMENTATION_STRUCTURE.md        [32] Canonical Tracked Documentation Architecture
```

---

## 3. Mapping of the 16 Required Project Domains

```
+----+----------------------------------+---------------------------------------------------------------+
| #  | Required Project Domain          | Canonical Tracked Documentation File(s)                       |
+----+----------------------------------+---------------------------------------------------------------+
| 1  | Project overview and features    | `README.md`                                                   |
| 2  | Architecture & major components  | `deployment/ARCHITECTURE.md`, `README.md`                     |
| 3  | Installation & local development | `README.md`, `frontend/README.md`                             |
| 4  | Environment configuration        | `deployment/RUNBOOK.md`, `deployment/.env.example`            |
| 5  | API usage and authentication     | `deployment/AUDIT_REPORT.md`, `README.md`                     |
| 6  | Database and migrations          | `deployment/AUDIT_REPORT.md`, `deployment/RUNBOOK.md`         |
| 7  | AI/ML pipeline architecture      | `deployment/ARCHITECTURE.md`, `evaluation/e2e/PROMPT_INVENTORY.md`|
| 8  | RAG, retrieval and indexing      | `evaluation/retrieval/README.md`, `deployment/ARCHITECTURE.md`|
| 9  | OCR and audio processing         | `deployment/P2_ML_RUNTIME_RELIABILITY_AUDIT.md`, `README.md`  |
| 10 | Testing and evaluation           | `deployment/TEST_MATRIX.md`, `evaluation/benchmark/README.md` |
| 11 | Docker and deployment            | `deployment/compose.yaml`, `deployment/docker-compose.prod.yml`|
| 12 | Production operations            | `deployment/RUNBOOK.md`, `deployment/PRODUCTION_VERIFICATION.md`|
| 13 | Backup and recovery              | `deployment/RUNBOOK.md`, `deployment/P2_PRODUCTION_PROMOTION_RECOMMENDATION.md`|
| 14 | Security                         | `deployment/RUNBOOK.md`, `deployment/AUDIT_REPORT.md`         |
| 15 | Contribution guidelines          | `README.md`, `deployment/CHANGE_REVIEW_REPORT.md`             |
| 16 | Important architectural decisions| `deployment/DEPLOYMENT_DECISIONS.md` (ADR 001 - ADR 008)      |
+----+----------------------------------+---------------------------------------------------------------+
```

---

## 4. Local-Only Preservation Policy

All 215 internal investigation notes, evaluation experiment runs, and forensic assessments remain preserved on disk.
They are safely untracked from Git via:
1. `git rm --cached` on the 143 historical evaluation files.
2. An explicit `.gitignore` section directing Git to ignore internal evaluation subdirectories and assessment folders without deleting the local files.

This achieves a permanent **79.2% reduction in tracked Markdown noise** (from 154 down to 32 files) while preserving 100% of the engineering evidence locally.
