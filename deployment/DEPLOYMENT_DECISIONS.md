# MediScanAI — Architectural & DevOps Deployment Decisions (ADR)

**Document Status:** Complete (Phase 1 Baseline)  
**Target Platform:** Oracle Cloud Always Free (Ampere A1 ARM64)  
**Budget Constraint:** Strictly ₹0 / month  

---

## 1. Decisions Already Made (Approved Baseline)

### ADR-01: Zero Monthly Cloud Budget (Conditional on Free Quotas & Account Configuration)
* **Context:** The project requires a cloud deployment for personal testing and demonstrations with zero recurring monthly infrastructure expenditure.
* **Decision:** Target the **Oracle Cloud Always Free Tier** specifically utilizing the Ampere A1 Compute shape (ARM64 architecture) which provides up to 4 OCPUs and 24 GB RAM permanently free.
* **Consequence:** All architecture, container builds, and dependency choices must be compatible with Linux ARM64 (`aarch64`).
* **Cost & Quota Boundary:** A ₹0 monthly operational spend is strictly conditional on account configuration. The application returning HTTP 503 upon provider exhaustion stops the software fallback loop, but does not configure external provider account billing. Administrators must ensure that third-party accounts (Google AI Studio, Groq Cloud) do not have active auto-billing credit cards or spend limits enabled that convert free quota exhaustion into paid charges. No guarantee of unlimited free API usage is made by external providers.

### ADR-02: Cloud AI Inference via Online APIs (No Local Cloud Ollama)
* **Context:** Running local 7B/8B LLM models (e.g. `llama3.1:8b`) on a cloud VM requires 6–8 GB of RAM and continuous CPU utilization, leaving minimal memory for OCR, embeddings, and web serving.
* **Decision:** In the cloud deployment, the backend will operate strictly in `LLM_MODE=online` using the configured 4-tier fallback chain (`GEMINI_MODEL_1: gemini-3.6-flash` $\rightarrow$ `GEMINI_MODEL_2: gemini-3.7-flash` $\rightarrow$ `GROQ_MODEL_1: openai/gpt-oss-120b` $\rightarrow$ `GROQ_MODEL_2: openai/gpt-oss-20b`).
* **Consequence:** Memory footprint avoids loading heavy local LLM weights (saving ~6–8 GB of RAM otherwise required by local Ollama/Mistral models); offloads generation to external online endpoints without local GPU requirements.
* **Cost & Quota Boundary:** The deployment relies strictly on eligible free-tier API quotas. Only eligible free-tier usage is intended; no paid fallback should be enabled without explicit administrative authorization. If all free quotas are exhausted or rate-limited (HTTP 429), the application returns a controlled `HTTP 503 Service Unavailable` response rather than routing to paid endpoints.

### ADR-03: Single Backend Container Topology (No Premature Microservices)
* **Context:** MediScanAI's current architecture features a FastAPI application tightly coupled with in-memory FAISS indexes, BM25 term matrices, SentenceTransformers, and PaddleOCR.
* **Decision:** Maintain a streamlined, 3-container production stack:
  1. `caddy` (Reverse proxy, automated TLS, rate limiting)
  2. `backend` (FastAPI + AI pipeline runtime)
  3. `postgres` (PostgreSQL 15 relational database)
* **Consequence:** Minimal operational complexity, straightforward Docker Compose management, fast inter-process communication without network serialization overhead.

### ADR-04: Preserve PaddleOCR as Sole Medication Extraction Engine
* **Context:** The medicine packaging OCR pipeline is validated and calibrated for clinical label extraction.
* **Decision:** Retain PaddleOCR without substituting alternative OCR engines (e.g. Tesseract or EasyOCR).
* **Consequence:** Container must include required native dependencies (`ffmpeg`, `libgomp1`, `libglib2.0-0`) and pre-compiled Linux aarch64 wheels for PaddlePaddle 3.0.

### ADR-05: Unified API Contract for React and Native iOS Clients
* **Context:** The current web client runs on React 19, while a native SwiftUI iPhone client is planned for future phases.
* **Decision:** Both clients will communicate with the identical `/api/analyze`, `/api/auth`, and `/api/analyses` endpoints.
* **Consequence:** No breaking changes to existing request/response schemas; all new features must maintain strict backwards compatibility.

---

### ADR-06: Two-Stage Minimal Production Dockerfile
* **Context:** A naive Dockerfile that installs build tools (`build-essential`, `gcc`, `g++`, `libffi-dev`) into the runtime container bloats image size and exposes compilers inside the production attack surface.
* **Decision:** Adopt a 2-stage build in `deployment/Dockerfile`:
  * Stage 1 (`builder`): Compiles dependencies into an isolated virtual environment (`/opt/venv`).
  * Stage 2 (`runtime`): Starts from a clean `python:3.10-slim`, installs only runtime dynamic libraries (`ffmpeg`, `libglib2.0-0`, `libgomp1`, `ca-certificates`), copies `/opt/venv`, and creates an unprivileged user (`appuser`, UID 1000).
* **Consequence:** Eliminates compilers from production image; enforces strict least-privilege non-root execution.

### ADR-07: Model Weight & Knowledge Asset Volume Mounting
* **Context:** MediScanAI relies on ~328 MB of precomputed FAISS indices and datasets, plus ~466 MB of HuggingFace, PaddleOCR, and Faster-Whisper weights. Baking these into the container image creates massive images that slow deployment transfers.
* **Decision:** Mount knowledge assets (`../data:/app/data:ro` and `../indexes:/app/indexes:ro`) as read-only host volumes. Mount model caches as a persistent named volume (`model_cache:/home/appuser/.cache`).
* **Consequence:** Image build context is reduced from >1 GB to 779 kB; container rebuilds and image updates do not require re-downloading model weights or transferring indices.

### ADR-08: Headless OpenCV Resolution (`opencv-python-headless`)
* **Context:** Root `requirements.txt` included both `opencv-python==4.12.0.88` and `opencv-contrib-python==4.10.0.84`. These packages collide in the Python site-packages namespace and pull in unnecessary X11/GUI libraries.
* **Decision:** In `deployment/requirements.txt`, replace both packages with a single `opencv-python-headless>=4.10.0.84`.
* **Consequence:** Zero X11/GUI dependencies; completely eliminates package shadowing and namespace collisions.

### ADR-09: Decouple Readiness Probe from Local Ollama
* **Context:** In `backend/main.py`, `/api/ready` checked `check_ollama_status()`. In cloud deployments where `LLM_MODE=online`, local Ollama is never started, causing the readiness probe to fail with 503 Service Unavailable.
* **Decision:** Make the Ollama check conditional: if `settings.LLM_MODE == "online"`, Ollama is bypassed and reported as `"not_required"`. If `settings.LLM_MODE == "offline"`, Ollama is probed as before.
* **Consequence:** Full backwards compatibility with local offline development; cloud readiness probe succeeds in `online` mode.

### ADR-10: Caddy Ingress Reverse Proxy & Automated TLS
* **Context:** Cloud deployment requires automated TLS certificate provisioning, security headers, request size limits, and internal network isolation without managing manual certbot cron jobs.
* **Decision:** Deploy official `caddy:2-alpine` as the ingress reverse proxy. Only Caddy publishes host ports 80 and 443. All backend and database communication is strictly isolated on the internal Docker bridge network (`mediscanai_internal_net`).
* **Consequence:** Automated Let's Encrypt certificates; HSTS, X-Content-Type-Options, X-Frame-Options, and Referrer-Policy injection; PostgreSQL port 5432 and backend port 8000 are completely inaccessible from the public internet.

---

## 2. Phase 3 Architecture & Provisioning Decisions

### ADR-11: Oracle Cloud Compute OS & Network Profile
* **Context:** Target cloud is Oracle Cloud Always Free Ampere A1.
* **Decision:** Provision an Ubuntu 24.04 LTS (aarch64) minimal instance with 2 OCPUs and 12 GB RAM. Configure Oracle VCN Security Lists and host UFW to permit ingress strictly on ports 22 (SSH), 80 (HTTP), and 443 (HTTPS).
* **Consequence:** Consistent, hardened Linux runtime matching our local Apple Silicon ARM64 testing.

---

## 3. Risk Assessment & Mitigation Strategies

| Risk ID | Risk Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :---: | :---: | :--- |
| **R-01** | **Dataset/Index Absence on Clean Git Clone** (`data/` and `indexes/` are in `.gitignore`) | **CRITICAL** | **HIGH** | Host directory `/opt/mediscanai/data` and `/indexes` will be securely transferred via `rsync`/`scp` and mounted read-only (`:ro`) into the container. |
| **R-02** | **Public Database Port Exposure** (`0.0.0.0:5432` exposed in dev compose) | **CRITICAL** | **HIGH** | Production Compose file will omit host port mapping for PostgreSQL, exposing port 5432 strictly to the internal Docker network. |
| **R-03** | **Hardcoded Secrets in Compose** | **HIGH** | **HIGH** | All credentials (`DATABASE_URL`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`) will be externalized to an uncommitted `.env.prod` file with `chmod 600` permissions. |
| **R-04** | **OpenCV Dual-Package Conflict** (`opencv-python` + `opencv-contrib-python`) | **HIGH** | **MEDIUM** | In Phase 2, consolidate dependencies to a single `opencv-python-headless` package in the container requirements. |
| **R-05** | **Readiness Probe Failure in Cloud** (`/api/ready` requiring Ollama) | **HIGH** | **HIGH** | Decouple readiness probe from Ollama when `LLM_MODE=online`. |
| **R-06** | **Cold-Start Model Download Timeout** | **MEDIUM** | **MEDIUM** | Mount host model cache directory as persistent Docker volume; execute warm-up script during initial host provisioning. |
| **R-07** | **Oracle Cloud Always Free VM Capacity Exhaustion** | **MEDIUM** | **LOW** | 2 OCPU / 12 GB RAM configuration leaves substantial RAM headroom above the locally observed ~1.64 GiB steady-state stack footprint (concurrent stress testing pending live cloud VM). |

