# MediScanAI — Phase 1: Complete Backend Deployment Audit & Infrastructure Baseline

**Audit Date:** 2026-11-15  
**Auditor:** Senior Backend, DevOps & AI Infrastructure Engineer  
**Repository:** `djcode0718/MediscanAI`  
**Git Branch:** `feature/cloud-docker-deployment`  
**HEAD Commit:** `fc5ad47a32db873d267340ac2857e0d00359ed32`  
**Target Cloud VM:** Oracle Cloud Always Free (Ampere A1 ARM64: 2 OCPUs, 12 GB RAM)  
**Budget Constraint:** Strictly ₹0 / month  

---

## 1. Executive Summary

A comprehensive, read-only Phase 1 engineering audit of MediScanAI has been completed. The purpose of this audit is to assess the deployment readiness of the existing multimodal health assistant backend, verify ARM64 architecture compatibility, execute baseline regression tests, identify security and infrastructure blockers, and establish a systematic implementation plan for Docker-based cloud deployment on Oracle Cloud Always Free.

### High-Level Verdict: Feasible with Target Mitigations
The MediScanAI backend **can realistically and comfortably run on a 2 OCPU / 12 GB RAM ARM64 Oracle Cloud VM** at zero monthly cost, provided the following critical conditions are met:
1. **Cloud LLM Routing:** Generation must operate strictly via online APIs (Google Gemini and Groq) using the existing 4-tier fallback chain. Local Ollama execution on the cloud VM is eliminated, saving 6–8 GB of RAM and significant CPU load.
2. **Readiness Probe Decoupling:** The `/api/ready` health probe must be decoupled from local Ollama so that it does not fail when `LLM_MODE=online`.
3. **Asset Volume Mounting:** The ~328 MB FAISS vector indexes and JSONL datasets (which are excluded from Git) must be transferred to the cloud host and mounted read-only into the container.
4. **Network & Credential Hardening:** Hardcoded development credentials in `docker-compose.yml` must be eliminated, and PostgreSQL port 5432 must be restricted to the internal Docker network rather than bound to `0.0.0.0`.
5. **OpenCV Package Resolution:** The conflicting dual-package declaration (`opencv-python` + `opencv-contrib-python`) must be consolidated into a single `opencv-python-headless` package for headless Linux containers.

---

## 2. Repository Structure

```text
/Users/sj/Documents/mediscanai
├── app/                        # Core AI, Retrieval & Clinical Pipeline
│   ├── core.py                 # Pipeline coordinator (RAG + Guardrails)
│   ├── retriever.py            # MultiRetriever (FAISS + BM25 + RRF + CrossEncoder)
│   ├── ocr.py                  # PaddleOCR lazy singleton text extraction
│   ├── whisper.py              # Faster-Whisper audio transcription (int8 CPU)
│   ├── embeddings.py           # SentenceTransformers ('all-MiniLM-L6-v2')
│   ├── llm.py                  # Local Ollama client & GenerationParams
│   ├── llm_providers.py        # Online LLM client (Gemini & Groq fallback chain)
│   ├── guardrail.py            # Emergency fast-path clinical triage guardrail
│   ├── evidence.py             # Provenance binding, formatting & hygiene
│   ├── prompt_v2.py            # Source-grounded clinical prompt templates (v1-v7)
│   ├── formatter.py            # Clinical summary card builder
│   ├── utils.py                # Standalone text & disease chunk normalizers
│   └── graph/                  # Optional Neo4j graph driver & retriever
├── backend/                    # FastAPI Web Application & Core Services
│   ├── main.py                 # FastAPI app, middleware, lifecycle events, /api/analyze
│   ├── api/                    # Routers: auth.py, analyses.py, deps.py
│   ├── core/                   # config.py, security.py, upload_validator.py, rate_limiter.py
│   ├── db/                     # session.py, base.py (SQLAlchemy 2.0 engine)
│   ├── models/                 # user.py, analysis.py, audit.py
│   └── schemas/                # auth.py, analysis.py (Pydantic models)
├── frontend/                   # React 19 + Vite User Interface (Desktop & Mobile)
├── alembic/                    # Database schema migrations (0001, 0002, 0003)
├── data/                       # JSONL knowledge bases (diseases, drugs, drug_dict) [~111 MB]
├── indexes/                    # Pre-computed FAISS vector indexes [~217 MB]
├── tests/                      # Application, unit, evaluation, and database tests
├── deployment/                 # Master deployment documentation & execution logs
├── Dockerfile                  # Existing single-stage container build manifest
├── docker-compose.yml          # Existing local development orchestration manifest
├── requirements.txt            # Python dependencies
└── .env.example                # Configuration template
```

---

## 3. Backend Architecture Analysis

### A. Lifecycle & Component Initialization
* **Startup Event (`@app.on_event("startup")`):**
  1. **PostgreSQL Connectivity:** Verified via `check_db_connection()`.
  2. **Pipeline Pre-warming (`get_pipeline()`):** Loads FAISS indexes (diseases, drugs, drug_dict), initializes in-memory BM25 term matrices, and pre-warms SentenceTransformers (`all-MiniLM-L6-v2`) and CrossEncoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
  3. **Faster-Whisper Pre-warming (`get_transcriber()`):** Instantiates `WhisperModel("base", compute_type="int8")`.
  4. **Emergency Guardrail:** Loads regex rule configuration from `app/guardrail_config.json`.
* **On-Demand Component:**
  * **PaddleOCR:** Instantiated lazily on first medicine image upload via thread-locked singleton in `app/ocr.py`. Initializing on first call takes ~2.5s; subsequent calls execute in ~250ms.

### B. Request Lifecycle for `/api/analyze`
1. **Authentication & Identity:** Validates HTTP Bearer token via `get_current_active_user`.
2. **Rate Limiting:** Enforces sliding-window rate limit (`settings.RATE_LIMIT_ANALYZE_PER_MINUTE`, default 10 req/min per user). Excess requests yield HTTP 429 with `Retry-After`.
3. **Concurrency Control:** `slot_manager.try_acquire()` enforces `MAX_CONCURRENT_ANALYSES` (default 2 simultaneous analyses) to protect CPU/RAM. Excess requests return HTTP 503 with `Retry-After: 5`.
4. **Input Validation:**
   * Text length capped at `MAX_TEXT_LENGTH` (default 5,000 characters).
   * Image magic bytes verified (JPEG `\xff\xd8\xff`, PNG `\x89PNG`, WebP `RIFF...WEBP`); size capped at 10 MB.
   * Audio magic bytes verified (WAV, MP3, WebM, OGG, M4A); size capped at 15 MB.
5. **Speech-to-Text:** If audio clips are attached, transcribed asynchronously off-thread via `asyncio.to_thread(transcriber.transcribe_audio_file)`.
6. **Vision OCR:** If an image is provided, OCR bounding boxes and text extracted via `asyncio.to_thread(pipeline.run)`.
7. **Clinical Triage Guardrail:** Checks combined symptoms/label text. If critical life-threatening conditions are detected (e.g. anaphylaxis, acute chest pain), immediately triggers fast-path emergency response without LLM generation.
8. **Dual-Channel Knowledge Retrieval:**
   * *Symptom Channel:* Queries `diseases` and `drugs` (for indications).
   * *Medication Channel:* Queries `drug_dict` and `drugs` (for package verification).
   * Each channel runs dense vector search + sparse BM25 + Reciprocal Rank Fusion ($k=60$) + Cross-Encoder reranking.
9. **Clinical Synthesis:** Calls online LLM provider (Gemini primary $\rightarrow$ Groq fallback) with source-grounded prompt requiring explicit chunk citation tags (`[E1]`, `[E2]`).
10. **Persistence & Audit:** Saves `Analysis` record to PostgreSQL with JSONB `summary_card` and timing metrics; logs operational audit event `ANALYSIS_CREATED`.
11. **Guaranteed Cleanup:** Concurrency slot released and temporary upload files unlinked in `finally` block.

---

## 4. API Contract Inventory

| HTTP Method | Endpoint Path | Summary / Purpose | Auth Required? | Request Payload | Response Schema | Frontend Binding (`frontend/src/config/api.js`) |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| `GET` | `/` | Root service liveness check | None | None | `{"status": "running", "app": "MediScanAI", ...}` | N/A (ping) |
| `GET` | `/api/health` | Fast Kubernetes/Docker liveness probe | None | None | `{"status": "alive", "timestamp": float}` | `API_ENDPOINTS.HEALTH` |
| `GET` | `/api/ready` | Readiness probe (DB, models, LLM) | None | None | `{"status": "ready", "components": {...}}` | `API_ENDPOINTS.READY` |
| `POST` | `/api/auth/register` | Register new user account | None | `UserRegisterRequest` (email, password, full_name) | `TokenResponse` (access_token, token_type, user) | `API_ENDPOINTS.AUTH_REGISTER` |
| `POST` | `/api/auth/login` | Authenticate user & issue JWT | None | `UserLoginRequest` (email, password) | `TokenResponse` (access_token, token_type, user) | `API_ENDPOINTS.AUTH_LOGIN` |
| `GET` | `/api/auth/me` | Fetch authenticated user profile | Bearer JWT | None | `UserResponse` (id, email, full_name, is_active) | `API_ENDPOINTS.AUTH_ME` |
| `POST` | `/api/analyze` | Multimodal clinical analysis | Bearer JWT | Multipart form: `text` (str), `image` (file), `audio` (files) | Dynamic analysis result dict (`card`, `meta`, `timings`, `analysis_id`) | `API_ENDPOINTS.ANALYZE` |
| `GET` | `/api/analyses` | Paginated user analysis history | Bearer JWT | Query params: `limit` (1-100), `offset` ($\ge 0$) | `AnalysisListResponse` (items, total, limit, offset) | `API_ENDPOINTS.ANALYSES` |
| `GET` | `/api/analyses/{id}` | Retrieve individual analysis detail | Bearer JWT | Path param: `analysis_id` (int) | `AnalysisDetailResponse` (id, modality, status, card, created_at) | `API_ENDPOINTS.ANALYSIS_DETAIL` |
| `DELETE`| `/api/analyses/{id}` | Delete individual analysis record | Bearer JWT | Path param: `analysis_id` (int) | `{"status": "deleted", "id": int}` | Dashboard history deletion |

---

## 5. Existing Docker & Compose Audit

### A. Dockerfile Deficiencies
1. **Single-Stage Build:** Retains compiler toolchains (`build-essential`, `gcc`, `g++`) in the final runtime container image, needlessly inflating image size by ~250 MB.
2. **Heavy GUI Dependencies:** Installs `libgl1`, `libsm6`, `libxext6`, `libxrender1` because `opencv-python` was declared instead of `opencv-python-headless`.
3. **Overly Broad Copy Directive:** `COPY --chown=appuser:appuser . /app` copies the entire working repository into the image because `.dockerignore` is insufficiently restrictive.
4. **Missing Production Optimization:** Does not compile `.pyc` wheels or strip cache layers.

### B. Docker Compose Deficiencies
1. **Critical Security Hole — Public Database Port Exposure:**
   ```yaml
   ports:
     - "5432:5432"  # EXPOSES POSTGRESQL TO PUBLIC INTERNET (0.0.0.0:5432)
   ```
   PostgreSQL port must be removed from the host mapping and confined strictly to the internal Docker network.
2. **Hardcoded Development Passwords:**
   `POSTGRES_PASSWORD: postgrespassword` and `JWT_SECRET_KEY=docker-local-development-secret-key-mediscanai-2026` are committed in plain text in `docker-compose.yml`.
3. **Hardcoded Ollama Readiness Expectation:**
   `OLLAMA_BASE_URL=http://host.docker.internal:11434` assumes a developer's desktop machine is running Ollama locally. In cloud production, Ollama is absent.
4. **Neo4j Port Exposure & Resource Overhead:**
   Exposes ports `7474` and `7687` to `0.0.0.0` for a service that is disabled by default (`NEO4J_ENABLED=false`).

### C. Build Context Bloat (.dockerignore)
The existing `.dockerignore` fails to exclude:
- `evaluation/` (144 files, benchmark datasets, evaluation runs)
- `results/` (historical benchmark reports)
- `deployment/` (audit documentation and logs)
- `.git/` (excluded, but large Git pack files can leak if modified)
- Local temporary files and IDE settings (`.vscode/`, `.idea/`)

---

## 6. Dataset, Index & Model Asset Inventory

| Asset Name | Expected Path | Size on Disk | Required for Startup? | Required for Analysis? | Source / Generation Method | Persistence Strategy |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **`diseases_faiss_data.jsonl`** | `data/diseases_faiss_data.jsonl` | 3.7 MB | **YES** | **YES** | Pre-computed disease symptom database | Read-only Docker volume mount |
| **`drug_dict_faiss_data.jsonl`** | `data/drug_dict_faiss_data.jsonl` | 2.9 MB | **YES** | **YES** | Brand-to-generic lookup dictionary | Read-only Docker volume mount |
| **`drugs_faiss_data.jsonl`** | `data/drugs_faiss_data.jsonl` | 103.4 MB | **YES** | **YES** | FDA drug label monographs & indications | Read-only Docker volume mount |
| **`diseases_faiss.index`** | `indexes/diseases_faiss.index` | 5.2 MB | **YES** | **YES** | Pre-computed 384-dim FAISS L2 index | Read-only Docker volume mount |
| **`drug_dict_faiss.index`** | `indexes/drug_dict_faiss.index` | 89.6 MB | **YES** | **YES** | Pre-computed drug dictionary vector index | Read-only Docker volume mount |
| **`drugs_faiss.index`** | `indexes/drugs_faiss.index` | 122.1 MB | **YES** | **YES** | Pre-computed FDA drug label vector index | Read-only Docker volume mount |
| **`all-MiniLM-L6-v2`** | `~/.cache/huggingface/hub/` | ~90 MB | **YES** | **YES** | Auto-downloaded from HuggingFace | Persistent Docker volume mount |
| **`ms-marco-MiniLM-L-6-v2`**| `~/.cache/huggingface/hub/` | ~90 MB | **YES** | **YES** | Auto-downloaded from HuggingFace | Persistent Docker volume mount |
| **`faster-whisper-base`** | `~/.cache/huggingface/hub/` | ~150 MB | **YES** | Only for audio | Auto-downloaded from HuggingFace | Persistent Docker volume mount |
| **PaddleOCR Detection/Rec**| `~/.paddlex/` | ~136 MB | NO (Lazy) | Only for image | Auto-downloaded from Paddle repository | Persistent Docker volume mount |

> [!IMPORTANT]
> **Total External Asset Volume:** ~328 MB (datasets + vector indexes) + ~466 MB (model weights) = **~794 MB total**.
> Because `data/` and `indexes/` are excluded from Git via `.gitignore`, they **must be transferred directly to the cloud VM** during deployment.

---

## 7. Memory & Resource Sizing for 12 GB ARM64 VM

### Component Memory Breakdown
```text
Component                       Idle / Startup RAM       Active Peak RAM
─────────────────────────────────────────────────────────────────────────
Linux Host OS (Ubuntu aarch64)         ~450 MB               ~550 MB
Caddy Reverse Proxy                     ~30 MB                ~50 MB
PostgreSQL 15 Database                  ~60 MB               ~150 MB
FastAPI + SQLAlchemy Base               ~80 MB               ~100 MB
FAISS Vector Indexes (in-memory)       ~220 MB               ~220 MB
BM25 In-Memory Term Matrices           ~280 MB               ~300 MB
SentenceTransformers (PyTorch CPU)     ~150 MB               ~200 MB
CrossEncoder Reranker                  ~150 MB               ~200 MB
Faster-Whisper (int8 CPU)              ~180 MB               ~250 MB
PaddleOCR (PaddlePaddle Engine)          0 MB (Lazy)         ~700 MB (When active)
─────────────────────────────────────────────────────────────────────────
TOTAL ESTIMATED MEMORY LOAD           ~1,600 MB (1.6 GB)    ~2,720 MB (2.7 GB)
```

### Headroom Analysis on Oracle Cloud Always Free
* **Total VM Memory:** 12,288 MB (12.0 GB)
* **Estimated Worst-Case Peak Load:** ~2,750 MB (2.75 GB)
* **Available Free Headroom:** **~9,500 MB (9.5 GB / ~77% buffer)**
* **Verdict:** The estimated memory footprint indicates substantial theoretical headroom within a 12 GB VM allocation. Live concurrent load testing on the cloud VM is required to establish actual production headroom under stress.

---

## 8. Security Findings & Risk Classification

| Finding ID | Severity | Category | Description | Recommended Remediation |
| :--- | :---: | :--- | :--- | :--- |
| **SEC-01** | **CRITICAL** | Network Exposure | Database port `5432:5432` is exposed to `0.0.0.0` in `docker-compose.yml`. | Remove host port mapping; confine PostgreSQL to internal Docker bridge. |
| **SEC-02** | **CRITICAL** | Credential Exposure| Hardcoded `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` in `docker-compose.yml`. | Move all credentials to `.env.prod`; inject via Docker Compose environment variables. |
| **SEC-03** | **HIGH** | Availability | `/api/ready` probe requires local Ollama service even when `LLM_MODE=online`. | Make Ollama check conditional on `LLM_MODE=offline`. |
| **SEC-04** | **HIGH** | Ingress Security | API exposed directly via Uvicorn without TLS or automated certificate management. | Place Caddy reverse proxy with automated Let's Encrypt TLS in front of FastAPI. |
| **SEC-05** | **MEDIUM** | Resource Waste | Neo4j service declared in Compose despite being disabled in configuration. | Remove `neo4j` container from minimal production compose stack. |
| **SEC-06** | **MEDIUM** | Package Hygiene | Conflicting dual OpenCV declarations (`opencv-python` + `opencv-contrib-python`). | Replace both with `opencv-python-headless` in container requirements. |
| **SEC-07** | **LOW** | Image Hygiene | Build tools (`gcc`, `g++`) retained in final Docker image layer. | Implement multi-stage Dockerfile. |

---

## 9. Baseline Test Results

All tests executed using the verified Conda environment (`/Users/sj/miniforge3/envs/med-env/bin/pytest`) on macOS Darwin ARM64:

1. **Application Core Suite:**
   * **Command:** `pytest tests/test_ocr.py tests/test_pipeline.py tests/test_no_benchmark_leakage.py tests/unit/test_crossfield_guard.py -v`
   * **Result:** **6 passed in 176.51s (100% pass rate)**.
   * **Log:** `deployment/logs/baseline_application_tests.log`
2. **Evaluation Engine Suite:**
   * **Command:** `pytest tests/unit/test_deterministic_checkers.py tests/unit/test_entity_attribution.py tests/unit/test_judge_input_parity.py tests/evaluation/ -v`
   * **Result:** **125 passed in 39.14s (100% pass rate)**.
   * **Log:** `deployment/logs/baseline_evaluation_tests.log`
3. **Broad Fast Suite (`run_tests.sh`):**
   * **Command:** `pytest tests/unit tests/api tests/database tests/test_e2e_smoke.py -v`
   * **Result:** **214 passed**, 4 failed (asserting optional A6.1 string formatting requiring `SANITIZER_A61=true`), 3 errors (local PostgreSQL server daemon not started on port 5432).

---

## 10. Recommended Changes for Phase 2 Implementation

The following files are slated for modification in Phase 2:
1. **`.dockerignore`**: Add exclusions for `evaluation/`, `results/`, `deployment/`, `.pytest_cache`, and temporary files.
2. **`Dockerfile`**: Refactor into a clean multi-stage build targeting Linux aarch64 with `opencv-python-headless`.
3. **`docker-compose.prod.yml`**: Author production orchestration manifest binding PostgreSQL internally, configuring Caddy TLS, and volume-mounting datasets and model caches.
4. **`Caddyfile`**: Configure automated Let's Encrypt HTTPS, security headers, and reverse proxy to `backend:8000`.
5. **`backend/main.py`**: Update `readiness_check` (`/api/ready`) to check Ollama only when `LLM_MODE=offline`.
6. **`requirements.txt`**: Create clean container-specific requirements or resolve OpenCV package declarations.

---

## 11. Confidence Assessment

* **ARM64 Compatibility Confidence:** **98%** (Pre-built wheels verified for all dependencies; final 2% requires executing containerized test build).
* **Memory & Resource Feasibility:** High confidence based on local steady-state measurements (~1.64 GiB) and estimated active load fitting within the 12 GB RAM envelope.
* **Budget Feasibility:** **100%** (Oracle Cloud Always Free provides 2 OCPU / 12 GB RAM permanently free; Gemini and Groq free tiers provide ample capacity for personal testing and demonstrations).

