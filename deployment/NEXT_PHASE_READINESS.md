# MediScanAI — Next-Phase Readiness Report

**Date:** 2026-11-16  
**Repository Baseline:** `main` @ `15d360ac84199147814503fb1955a50cacd1b470`  
**Target Deployment Infrastructure:** Oracle Cloud Always Free (`VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM, ARM64)  
**Client Targets:** Existing React 19 Frontend + Future Native iOS (SwiftUI) Client  

---

## 1. Architectural Baseline

The MediScanAI platform baseline on `main` is structured as a decoupled, multi-tier system:

```
[ Clients ]
   ├── Web Client (React 19, TypeScript, TailwindCSS, Vite)
   └── Future Mobile Client (Native iOS SwiftUI Client)
             │
             ▼ (HTTPS / JSON + Multipart Form Data)
[ Ingress & Security ]
   └── Caddy 2.8 Reverse Proxy (Automated TLS, Rate Limiting, Security Headers)
             │
             ▼ (Internal Docker Bridge Network: mediscanai_internal_net)
[ Core Application Tier ]
   └── FastAPI (Python 3.11, Uvicorn, Lifespan Pre-warming)
         ├── Auth & User Management (JWT, Argon2id)
         ├── Upload Validation & Quarantine (/api/upload, extension sanitization)
         ├── Multi-modal Processing:
         │     ├── OCR Engine: PaddleOCR v2.9 (pre-warmed on lifespan startup)
         │     ├── Audio Transcription: Faster-Whisper (CTranslate2 CPU)
         │     └── Clinical Analysis Pipeline (Prompt v2, Structured JSON)
         ├── Hybrid Retrieval Engine (Dense FAISS + Sparse BM25 + Reciprocal Rank Fusion)
         ├── LLM Provider Resilience (Zero-Cost Chain: Gemini 3.6/3.7 Flash -> Groq GPT-OSS 120B/20B)
         └── Audit & Compliance Logger (Isolated database transactions, durable audit records)
             │
             ▼ (PostgreSQL Wire Protocol)
[ Persistence Tier ]
   └── PostgreSQL 16 (Relational DB, Alembic Migrations, Docker Named Volume)
```

---

## 2. Completed Work (Phase 1, 2 & PR #1 Integration)

1. **Docker Footprint & CPU-Only ARM64 Optimization**:
   - Eliminated 3.3 GB of dead NVIDIA CUDA/Triton binaries from the ARM64 deployment container.
   - Reduced uncompressed container footprint from 11.66 GB to 5.46 GB (-53%) and compressed distribution package to 1.76 GB (-55%).
   - Retained complete CPU wheels for PyTorch 2.5.1, PaddlePaddle 3.0.0, FAISS-CPU 1.7.4, and CTranslate2 4.5.0.

2. **Lifespan Startup Sequencing & Pre-warming**:
   - Implemented lifespan warm-up hook in `backend/main.py` executing a dummy OCR pass on a synthetic blank image during startup.
   - Pre-initializes C++ runtime threads and LCNet model weights before ingress traffic arrives, eliminating OpenMP thread collision segfaults (`libgomp.so`).
   - Extended Docker compose healthcheck `start_period` to 180s to accommodate warm-up.

3. **Decoupled Readiness & Health Probes**:
   - Decoupled `/api/ready` from local Ollama service when running in online LLM mode (`LLM_MODE=online`), returning HTTP 200 with `ollama_service: "not_required"`.
   - Exposed structured diagnostic payload covering database reachability, OCR warmup status, and LLM readiness.

4. **Upload Security & Filename Sanitization**:
   - Added regex-based extension sanitization in `backend/core/upload_validator.py` stripping trailing dots, spaces, and non-printable characters to mitigate double-extension and null-byte bypasses.

5. **Database Transaction Ownership & Audit Durability**:
   - Refactored `backend/core/audit.py` to decouple audit logging sessions from caller transactions using engine-bound isolated sessions (`Session(bind=db.get_bind())`).
   - Guaranteed that audit records are persistently written even if caller requests roll back or encounter downstream HTTP exceptions, while never prematurely committing caller transactions.

6. **Repository Hygiene & Documentation Rationalization**:
   - Cleaned up Git index from 152 tracked Markdown files down to exactly 26 canonical operational documents.
   - Preserved all 225 historical investigation documents and benchmark evaluation reports on local disk.
   - Hardened `.dockerignore` and `.gitignore` to keep Docker build context under 800 kB.

7. **PR #1 Integration into `main`**:
   - Successfully merged PR #1 into `main` via GitHub PR API (`15d360a`), preserving all 8 discrete feature branch commits in the project history.

---

## 3. Remaining Work (Phase 3: Cloud Provisioning)

| Work Item | Component | Current State | Required Action | Priority |
| :--- | :--- | :--- | :--- | :---: |
| **OCI Always Free VM Provisioning** | Cloud Infrastructure | Awaiting tenancy access | Provision `VM.Standard.A1.Flex` (2 OCPU, 12 GB RAM, Ubuntu 24.04 ARM64 minimal) in Oracle Cloud console. | **P0** (Blocker) |
| **Cloud Host Hardening** | OS / Security | Documented in `RUNBOOK.md` | Configure UFW (ports 22, 80, 443), SSH key authentication, disable root password login, install fail2ban. | **P0** |
| **Docker Engine & Stack Installation** | Container Runtime | Documented in `RUNBOOK.md` | Install Docker Engine & Compose v2 on cloud host; clone repository `main` branch. | **P0** |
| **FAISS Indexes & Model Assets Transfer** | Data Storage | ~328 MB assets on local host | Rsync `/data` and `/indexes` directories to cloud host read-only mounts. | **P0** |
| **Production Environment Secret Injection** | Secrets Management | `.env.example` in repo | Create cloud `/deployment/.env` with secure PostgreSQL password, JWT secret, and API keys. | **P0** |
| **DNS & Automated TLS Provisioning** | Ingress / Caddy | Configured in `Caddyfile` | Point user domain A-record to VM public IP; verify Let's Encrypt certificate issuance. | **P1** |
| **End-to-End Live Cloud Verification** | Validation Suite | Verified locally | Run smoke tests against live public HTTPS domain. | **P1** |

---

## 4. Technical Debt & Architectural Watchpoints

1. **Test Suite Database Mocking**:
   - Integration tests in `tests/database/` require a live PostgreSQL instance on `localhost:5432`.
   - *Recommendation:* Standardize integration test fixtures using `pytest-postgresql` or Docker testcontainers to allow offline local CI runs without requiring a persistent host PostgreSQL daemon.

2. **In-Memory SQLite vs PostgreSQL Dialect Differences**:
   - Unit tests use SQLite in-memory databases with mocked JSONB and UUID types.
   - *Recommendation:* Keep SQLite-specific type compatibility shims confined to test fixtures; never compromise PostgreSQL production schemas to suit SQLite limitations.

3. **Historical Evaluation Dataset Storage**:
   - Untracked evaluation datasets (~100 MB) are preserved locally on disk but not in Git index.
   - *Recommendation:* Set up a dedicated object storage bucket (e.g. OCI Object Storage Always Free or HuggingFace Datasets) to version evaluation benchmarks for future model retraining.

4. **Multi-worker Concurrency vs OpenMP/PaddleOCR**:
   - PaddleOCR C++ libraries allocate internal thread pools. Uvicorn is currently configured to run 1 worker with 2 threads.
   - *Recommendation:* Do not scale Uvicorn `--workers` beyond 2 on the 2 OCPU VM. To scale throughput, scale horizontally or introduce a Celery/Redis asynchronous task queue for OCR and audio processing.

---

## 5. Mobile Client Readiness: Native iOS (SwiftUI) Backend API Contracts

A future native SwiftUI iOS application is planned to consume the MediScanAI backend API alongside the existing React frontend. To ensure zero-friction client integration:

### API Contract Rules:
1. **Strict Transport & Content Types**:
   - All client-to-server payloads must remain strict JSON (`application/json`) or standard RFC 7578 multipart form-data (`multipart/form-data`) for document uploads.
   - Avoid frontend-specific assumptions (e.g. browser cookies or browser-dependent session headers). Use RFC 6750 `Authorization: Bearer <token>` headers uniformly.
2. **Schema Stability & Pydantic Validation**:
   - Maintain OpenAPI 3.1 compliance on all `/api/*` endpoints. Both clients should be able to generate type-safe client models (TypeScript interfaces for React, Swift `Codable` structs for iOS) directly from `/api/openapi.json`.
3. **Pagination & Sizing for Mobile Payloads**:
   - `/api/analyses` and historical logs must provide explicit `limit` and `offset` pagination to prevent excessive cellular data consumption and iOS memory pressure.
4. **Idempotency & Network Resilience**:
   - Mobile network transitions (Wi-Fi to 5G) can cause dropped connections. Critical operations (e.g., submitting an analysis) should support client-generated `X-Request-ID` or idempotency keys.
5. **Streaming Diagnostics**:
   - For long-running multimodal analysis (OCR + RAG + LLM inference, 5-20s), consider adding Server-Sent Events (SSE) via `/api/analyze/stream` so mobile clients can display interactive step-by-step progress bars (e.g. "Extracting text...", "Searching medical index...", "Generating clinical report...").

---

## 6. Prioritized Implementation Sequence for Next Phase

```
[ Step 1: Tenancy & Compute Provisioning ] (BLOCKED on user credentials)
  - Provision OCI VM.Standard.A1.Flex (2 OCPU, 12 GB RAM)
  - Configure Security Lists & VCN Ingress (22, 80, 443)
       │
       ▼
[ Step 2: Host Preparation & Security Hardening ]
  - Execute automated host setup script from RUNBOOK.md
  - Verify Docker Engine 27+ and Compose v2
       │
       ▼
[ Step 3: Deployment & Asset Sync ]
  - Clone repository main branch on cloud host
  - Rsync data/ and indexes/ (~328 MB)
  - Configure production deployment/.env
       │
       ▼
[ Step 4: Container Stack Launch ]
  - Run `docker compose -f compose.yaml -f docker-compose.prod.yml up -d`
  - Verify database migrations (0001, 0002, 0003)
  - Verify Caddy reverse proxy and Let's Encrypt TLS
       │
       ▼
[ Step 5: Smoke & Performance Verification ]
  - Execute live API health & readiness probes
  - Verify React web frontend connectivity
  - Conduct baseline latency profiling and memory monitoring
```
