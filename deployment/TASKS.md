# MediScanAI — Master Deployment Task Tracker

**Target Cloud:** Oracle Cloud Always Free (Ampere A1 ARM64: 2 OCPUs, 12 GB RAM)  
**Budget:** Strictly ₹0/month  
**Development Machine:** MacBook Air M4 (macOS ARM64)  
**Client Targets:** Existing React 19 Frontend + Future Native iOS (SwiftUI) Client  
**Current Phase:** Phase 3 — Cloud Provisioning & Deployment

---

## Task Status Legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed
- `[!]` Blocked

---

## Phase 1: Audit, Baseline & Infrastructure Feasibility

| Task ID | Description | Status | Priority | Dependencies | Evidence Required | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **P1-T01** | Inspect Git state and establish clean working baseline | `[x]` | P0 | None | `git status`, `git branch -vv` | Branch `feature/cloud-docker-deployment` at commit `fc5ad47`. |
| **P1-T02** | Map FastAPI lifecycle, routers, and request pipeline flow | `[x]` | P0 | P1-T01 | `deployment/AUDIT_REPORT.md`, `deployment/ARCHITECTURE.md` | Documented startup events, lazy singletons, middleware, and `/api/analyze` lifecycle. |
| **P1-T03** | Compile exhaustive API endpoint contract inventory | `[x]` | P0 | P1-T02 | `deployment/AUDIT_REPORT.md` (Section 4) | Documented all 9 endpoints, auth requirements, Pydantic schemas, and frontend bindings. |
| **P1-T04** | Audit existing `Dockerfile` and `docker-compose.yml` | `[x]` | P0 | P1-T01 | `deployment/AUDIT_REPORT.md` (Section 5) | Identified hardcoded secrets, open 0.0.0.0 DB ports, missing context exclusions, and build layers. |
| **P1-T05** | Inventory datasets, FAISS indexes, and model assets | `[x]` | P0 | P1-T02 | `deployment/AUDIT_REPORT.md` (Section 6) | Cataloged ~328 MB FAISS/JSONL assets, HF cache, PaddleOCR weights, and runtime persistence requirements. |
| **P1-T06** | Conduct 3-way CPU architecture dependency audit | `[x]` | P0 | P1-T04 | `deployment/DEPENDENCY_COMPATIBILITY.md` | Verified PyPI `manylinux2014_aarch64` wheels for PaddlePaddle 3.0, FAISS-CPU 1.7.4, Torch, and CTranslate2. |
| **P1-T07** | Execute and log baseline test suites (App, Eval, Unit) | `[x]` | P0 | P1-T01 | `deployment/logs/*.log`, `deployment/TEST_MATRIX.md` | Baseline: 6/6 core app tests passed; 125/125 eval tests passed; 214/221 fast unit tests passed (3 DB tests blocked by absence of local PostgreSQL daemon, 4 evidence-hygiene tests flagged). |
| **P1-T08** | Profile memory and compute footprint for 12 GB ARM64 VM | `[x]` | P1 | P1-T05 | `deployment/AUDIT_REPORT.md` (Section 8) | Estimated peak container memory ~2.5 GB; well within 12 GB RAM budget. |
| **P1-T09** | Conduct security, auth, and production readiness review | `[x]` | P0 | P1-T04 | `deployment/AUDIT_REPORT.md` (Section 9) | Classified findings into Critical (hardcoded compose secrets, public DB ports), High, Medium, Low. |
| **P1-T10** | Produce Phase 1 deliverables and master architectural blueprint | `[x]` | P0 | P1-T01-09 | `deployment/` artifacts created | Complete suite of 7 Markdown audit reports and logs generated. |

---

## Phase 2: Docker Engineering, ARM64 Optimization & Local Validation

| Task ID | Description | Status | Priority | Dependencies | Evidence Required | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **P2-T01** | Harden `.dockerignore` to exclude evaluation, tests, and caches | `[x]` | P0 | Phase 1 Complete | `.dockerignore`, build context: 779 kB | Context transfer shrunk to 779 kB (excluded `evaluation/`, `results/`, `data/`, `indexes/`, test caches). |
| **P2-T02** | Resolve OpenCV dependency conflict in `requirements.txt` | `[x]` | P0 | Phase 1 Complete | `deployment/requirements.txt` | Replaced colliding `opencv-python` and `opencv-contrib-python` with `opencv-python-headless>=4.10.0.84`. |
| **P2-T03** | Decouple `/api/ready` probe from local Ollama service | `[x]` | P0 | Phase 1 Complete | `backend/main.py`, `tests/api/test_health_and_readiness.py` | Readiness probe returns 200 with `ollama_service: "not_required"` when `LLM_MODE=online`. 6/6 health/readiness unit tests passed. |
| **P2-T04** | Author production-grade multi-stage `Dockerfile` | `[x]` | P0 | P2-T01, P2-T02 | `deployment/Dockerfile` | Two-stage build: builder builds venv; runtime strips GCC/build tools, UID 1000 `appuser`, healthcheck with 180s start-period. |
| **P2-T05** | Build and test ARM64 container image locally on Apple Silicon | `[x]` | P0 | P2-T04 | `mediscanai-backend:production` | Built image `mediscanai-backend:production` on macOS M4 (LinuxKit aarch64 kernel). Verified imports of `cv2`, `paddle`, `faiss`, `torch`, `faster_whisper`. (Local verification; distinct from live OCI VM). |
| **P2-T06** | Author production `deployment/compose.yaml` and `.prod.yml` | `[x]` | P0 | P2-T04 | `deployment/compose.yaml`, `deployment/.env.example` | Zero public host exposure on DB/backend, internal bridge network `mediscanai_internal_net`, production resource limits. |
| **P2-T07** | Configure Caddy reverse proxy with automated TLS | `[x]` | P0 | P2-T06 | `deployment/Caddyfile` | Ingress reverse proxy configuration with HSTS, X-Content-Type-Options, X-Frame-Options, 30MB upload limits. (Local testing verified over HTTP :80; public Let's Encrypt TLS pending cloud domain). |
| **P2-T08** | Verify volume mounting for FAISS indexes and dataset files | `[x]` | P0 | P2-T06 | `docker run -v ... ls -la /app/data /app/indexes` | Verified read-only host mounts (`../data:/app/data:ro` and `../indexes:/app/indexes:ro`). Model cache mounted to `/home/appuser/.cache`. |
| **P2-T09** | Execute database migration (`alembic upgrade head`) in container | `[x]` | P0 | P2-T06 | `docker logs mediscanai-backend` | Migrations `0001_initial_schema`, `0002_add_user_full_name`, `0003_analysis_and_audit` applied cleanly to container PostgreSQL. |
| **P2-T10** | Perform end-to-end API verification inside local container stack | `[x]` | P0 | P2-T08, P2-T09 | `deployment/logs/phase2_runtime_verification.log` | Tested `/api/auth/register` (201), `/api/auth/login` (200), `/api/analyses` (200), and text-only `/api/analyze` (200 in 31.98s via online fallback). Multimodal OCR verified via `test_ocr.py`. |
| **P2-T11** | Profile container resource consumption under local baseline load | `[x]` | P1 | P2-T10 | `docker stats --no-stream` | Point-in-time steady-state snapshot: Backend ~1.59 GiB RAM (39.8% of 4GB limit); Caddy: 21.4 MiB; Postgres: 22.5 MiB. Stack total: ~1.64 GiB. (Single-request snapshot; not a peak stress test). |
| **P2-T12** | Execute P0 Docker resource cleanup and reconcile disk savings | `[x]` | P0 | P2-T11 | `deployment/P2_DOCKER_STORAGE_AUDIT.md` | Purged stopped Neo4j container (172 MB), obsolete image (889 MB), log volume (203 KB), and dangling image (3.09 GB). Exactly 4.15 GB reclaimed. |
| **P2-T13** | Engineer and validate CPU-only ARM64 backend Docker image (P1) | `[x]` | P0 | P2-T12 | `deployment/Dockerfile.cpu`, `deployment/requirements-cpu.txt` | Shrunk uncompressed backend image from 11.66 GB to 3.85 GB (-67%) and compressed archive to 865 MB (-78%). Removed 3.3 GB of CUDA/Triton binaries. |
| **P2-T14** | Conduct comprehensive Docker footprint & runtime memory audit (P2) | `[x]` | P0 | P2-T13 | `deployment/P2_*.md` deliverables | Complete audit suite: Storage reconciliation, Mac memory sizing, Neo4j reachability, OpenMP thread collision mitigation, regression suite (235/239 pass), and promotion runbook. |
| **P2-T15** | Execute Final Production Promotion Gate & SRE Reliability Verification | `[x]` | P0 | P2-T14 | `deployment/FINAL_PROMOTION_GATE_REPORT.md` | Pre-warmed PaddleOCR, resolved OpenMP LCNet segfault, 162/162 production tests passing (100% across 3 runs), empirical rollback RTO measured at 101.96s, compose start_period validated. |
| **P2-T16** | Repository documentation rationalization and Git cleanup | `[x]` | P0 | P2-T15 | `deployment/GIT_CLEANUP_FINAL_REPORT.md` | Reduced tracked Markdown files from 152 to 26 canonical docs; preserved 225 local historical docs; hardened ignore files. |
| **P2-T17** | Audit and reconcile PR #1 code, LLM chain & transaction ownership | `[x]` | P0 | P2-T16 | `deployment/CHANGE_REVIEW_REPORT.md`, commit `369288e` | Reconciled LLM docstrings to Gemini 3.6/3.7 & Groq 120B/20B; isolated audit transaction ownership; added automated test. |
| **P2-T18** | Merge PR #1 into `main` and author next-phase readiness documentation | `[x]` | P0 | P2-T17 | `deployment/MERGE_FINAL_REPORT.md`, `deployment/NEXT_PHASE_READINESS.md` | PR #1 merged into `main` via merge commit `15d360a`; full 8-commit history preserved; verified 237 unit tests and frontend build. |

---

## Phase 3: Oracle Cloud Always Free Provisioning & Deployment

| Task ID | Description | Status | Priority | Dependencies | Evidence Required | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **P3-T01** | Verify Oracle Cloud Always Free tier and tenancy allowances | `[!]` | P0 | Phase 2 Complete | Tenancy console verification | **BLOCKED:** Awaiting user tenancy verification (no local OCI CLI credentials in environment). |
| **P3-T02** | Provision VM.Standard.A1.Flex instance (2 OCPU, 12 GB RAM) | `[!]` | P0 | P3-T01 | Instance details, public IP | **BLOCKED:** Requires user provisioning in OCI Console or SSH access to target instance. Target: Ubuntu 24.04 LTS aarch64 minimal. Strictly ₹0 Always Free tier. |
| **P3-T03** | Harden Linux host (SSH keys, UFW/iptables, disable root login) | `[ ]` | P0 | P3-T02 | `ssh -V`, firewall status | Not started. Script documented in `deployment/RUNBOOK.md`. |
| **P3-T04** | Install Docker Engine, Docker Compose, and fail2ban on cloud VM | `[ ]` | P0 | P3-T03 | `docker --version`, Compose v2 | Not started. Automated installation sequence documented in `deployment/RUNBOOK.md`. |
| **P3-T05** | Securely transfer dataset files, FAISS indexes, and `.env.prod` | `[ ]` | P0 | P3-T04 | `rsync`/`scp` transfer verification | Not started. `rsync` commands for `data/` and `indexes/` (~328 MB) documented. |
| **P3-T06** | Deploy production container stack (`docker compose -f ... up -d`)| `[ ]` | P0 | P3-T05 | `docker ps`, container health checks | Not started. Compose stack verified locally in Phase 2. |
| **P3-T07** | Configure DNS records and verify automated Let's Encrypt SSL | `[ ]` | P0 | P3-T06 | HTTPS curl test, TLS certificate expiry | Not started. Requires user-configured DNS A-record pointing to VM public IP. |
| **P3-T08** | Execute smoke & integration tests against live cloud URL | `[ ]` | P0 | P3-T07 | `test_cloud_e2e.py` log | Not started. Local container tests passed; live cloud execution pending. |
| **P3-T09** | Validate React frontend connection to live cloud backend | `[ ]` | P0 | P3-T08 | Frontend browser verification | Not started. Requires live cloud URL. |
| **P3-T10** | Perform restart resilience and automated reboot testing on cloud VM | `[ ]` | P1 | P3-T09 | VM reboot test, container restart logs | Not started. Service restart policy verified locally; cloud VM reboot pending. |
| **P3-T11** | Establish backup routines and prepare rollback runbook | `[~]` | P1 | P2-T06, P2-T09 | `deployment/RUNBOOK.md` | **In Progress / Partial:** Procedures authored and verified in local Docker containers; cloud host execution and scheduled automation pending. |

---

## Phase 4: Future Enhancements & Production Hardening (Post-Deployment)

| Task ID | Description | Status | Priority | Dependencies | Evidence Required | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **P4-T01** | Expand LLM Fallback Chain with Additional Zero-Cost Providers | `[ ]` | P2 | Phase 3 Complete | Provider audit log, test suite, latency metrics | Future task to enhance resilience against API rate-limits and regional outages while preserving zero-cost budget constraint. |

### P4-T01 Requirements & Acceptance Criteria:
1. **Provider Research**: Research additional eligible zero-cost / free-tier LLM providers and models (e.g., Cloudflare Workers AI, HuggingFace Inference API, GitHub Models, Cohere, Mistral).
2. **Identifier Verification**: Verify current live API availability and exact supported model identifiers directly against active documentation and test invocations.
3. **Quota & Terms Inspection**: Inspect rate limits (RPM/RPD/TPM), quota policies, concurrency thresholds, and terms of service regarding data handling and privacy.
4. **Structured JSON Compatibility**: Benchmark structured JSON output, schema fidelity, tool calling (if needed), and clinical prompt compatibility.
5. **Latency Profiling**: Measure end-to-end response latency, time-to-first-token (TTFT), and failure/retry rates across candidate models.
6. **Graceful Fallback Mechanics**: Implement client-side timeouts, exponential backoff, circuit breaking, and seamless handoff to next provider in chain without service disruption.
7. **Zero-Cost Enforcement**: Enforce strict zero-cost budget boundary: guarantee that no fallback path can silently route to a paid tier or incur billed credit usage without explicit administrative opt-in.
8. **Fault Injection Testing**: Conduct automated fault-injection testing simulating provider downtime, HTTP 429 rate limits, and quota exhaustion to verify graceful degradation to informative HTTP 503 errors.

