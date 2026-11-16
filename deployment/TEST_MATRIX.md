# MediScanAI — Three-Phase Deployment Verification & Test Matrix

**Document Version:** 1.0.0 (Phase 1 Baseline)  
**Host Environment:** macOS Darwin ARM64 (Apple Silicon M4) / Python 3.10.18 (`med-env`)  
**Target Cloud VM:** Linux aarch64 (Oracle Cloud Always Free Ampere A1: 2 OCPU, 12 GB RAM)  

---

## Status Classification Key
- **PASS**: Executed with exit code 0; assertions passed completely.
- **FAIL**: Executed; one or more assertions or execution steps failed.
- **BLOCKED**: Could not be executed due to missing environmental prerequisite (e.g. offline daemon).
- **NOT RUN**: Planned for future phase; not yet scheduled for execution.
- **PARTIAL**: Partially executed; some assertions verified, remainder deferred.

---

## 1. Phase 1: Baseline & Pre-Deployment Test Matrix

| Test ID | Component | Test Description | Command / Procedure | Expected Outcome | Actual Outcome | Status | Evidence / Log Reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **T1-APP-01** | OCR Vision | Synthetic label generation & text extraction without local paths | `pytest tests/test_ocr.py -v` | Extracts simulated drug name text with PaddleOCR; zero external file dependencies | 1/1 tests passed; genuine text regions extracted and verified | **PASS** | `deployment/logs/baseline_application_tests.log` |
| **T1-APP-02** | RAG Pipeline | Text-only symptom inquiry flow (retrieval + prompt + LLM) | `pytest tests/test_pipeline.py -k text_only -v` | Retrieves diseases and drugs; formats response with non-empty verdict | 1/1 tests passed; end-to-end pipeline returned complete summary card | **PASS** | `deployment/logs/baseline_application_tests.log` |
| **T1-APP-03** | RAG Pipeline | Multimodal symptom + synthetic label OCR flow | `pytest tests/test_pipeline.py -k multimodal -v` | Extracts OCR text, performs dual-channel retrieval, returns verified response | 1/1 tests passed; multimodal pipeline completed with full timings | **PASS** | `deployment/logs/baseline_application_tests.log` |
| **T1-APP-04** | Runtime Isolation | AST static scan verifying zero application imports from `evaluation/` | `pytest tests/test_no_benchmark_leakage.py -v` | Scan detects 0 import paths referencing `evaluation` across `app/` and `backend/` | 1/1 tests passed; 0 evaluation imports confirmed across 17 modules | **PASS** | `deployment/logs/baseline_application_tests.log` |
| **T1-APP-05** | Clinical Guard | Cross-field indication and symptom hygiene isolation | `pytest tests/unit/test_crossfield_guard.py -v` | Prevents patient symptoms from falsely attributing to OCR packaging | 2/2 tests passed; cross-field and sufficiency evaluations verified | **PASS** | `deployment/logs/baseline_application_tests.log` |
| **T1-EVAL-01** | Evaluation Engine | Calibrated evaluator, absence scanner, and atomic decomposer | `pytest tests/evaluation/ -v` | Comprehensive unit verification of isolated judging framework | 114/114 evaluation tests passed | **PASS** | `deployment/logs/baseline_evaluation_tests.log` |
| **T1-EVAL-02** | Deterministic Checks| Parity checks, entity attribution, and deterministic checkers | `pytest tests/unit/test_deterministic_checkers.py tests/unit/test_entity_attribution.py tests/unit/test_judge_input_parity.py -v` | AST and deterministic parsing pass with 100% parity | 11/11 tests passed | **PASS** | `deployment/logs/baseline_evaluation_tests.log` |
| **T1-SEC-01** | Upload Validator | Image magic byte validation (JPEG, PNG, WebP) and size limits | `pytest tests/unit/test_security_and_bounds.py -k image -v` | Rejects spoofed extensions; accepts authentic binary headers | Passed in full fast suite | **PASS** | Fast test suite run |
| **T1-SEC-02** | Upload Validator | Audio magic byte validation (WAV, MP3, WebM, OGG, M4A) | `pytest tests/unit/test_security_and_bounds.py -k audio -v` | Rejects non-audio payloads; enforces 15MB file cap | Passed in full fast suite | **PASS** | Fast test suite run |
| **T1-SEC-03** | Auth & JWT | Bcrypt password hashing (round 12) & JWT creation/expiration | `pytest tests/unit/test_auth_unit.py -v` | Verifies secure password verification and token expiration | Passed in full fast suite | **PASS** | Fast test suite run |
| **T1-DB-01** | PostgreSQL | PostgreSQL connection, JSONB querying, rollback validation | `pytest tests/database/test_database_postgres.py -v` | Connects to PostgreSQL and verifies JSON storage | **BLOCKED:** Local PostgreSQL daemon on port 5432 is not running on macOS host | **BLOCKED** | Documented in Phase 1 audit |
| **T1-DOCK-01** | Docker CLI | Check local Docker installation and daemon status | `docker --version && docker compose version` | Docker CLI and Compose available | Docker 29.8.2 and Compose v5.6.0 installed; daemon currently stopped | **PASS** | `deployment/logs/docker_inspection.log` |

---

## 2. Phase 2: Verified Container & ARM64 Test Matrix (Local Apple Silicon Environment)

> **Important Environmental Scope:**  
> Phase 2 testing was performed locally on an Apple Silicon (M4) ARM64 host running Docker Engine (LinuxKit aarch64 kernel). This validates Linux ARM64 binary and container compatibility, but is distinct from live cloud execution on an Oracle Cloud Infrastructure (OCI) Ampere A1 VM.

| Test ID | Component | Test Description | Command / Procedure | Expected Outcome | Actual Outcome | Status | Evidence / Log Reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **T2-DOCK-01** | Docker Build | Build multi-stage production Docker image on macOS ARM64 | `docker build -f deployment/Dockerfile -t mediscanai-backend:production .` | Image compiles without errors; Linux aarch64 manifest | 2-stage build succeeded on Apple Silicon M4; context: 779 kB; image tag: `mediscanai-backend:production` | **PASS** | `deployment/logs/phase2_runtime_verification.log` |
| **T2-DOCK-02** | OpenCV Headless | Verify absence of GUI dependencies in container | `docker run --rm mediscanai-backend:production python -c "import cv2; print(cv2.__version__)"` | OpenCV imports cleanly without X11 or OpenGL shared libraries | `cv2 version: 4.10.0` (headless) imported cleanly with UID 1000 | **PASS** | Verified in container runtime |
| **T2-DOCK-03** | PaddleOCR ARM64 | Verify PaddleOCR & PaddlePaddle inside container | `docker run --rm mediscanai-backend:production python -c "import paddle, paddleocr; print(paddle.__version__)"` | PaddlePaddle initializes without illegal instruction on aarch64 | `paddle version: 3.0.0`, PaddleOCR initialized cleanly | **PASS** | Verified in container runtime |
| **T2-DOCK-04** | FAISS Vector Search | Verify FAISS-CPU index loading and vector search inside container | `docker run --rm -v $(pwd)/indexes:/app/indexes:ro mediscanai-backend:production python -c "import faiss; print(faiss.__file__)"` | All 3 FAISS indexes load within 2 seconds | `faiss` loaded cleanly; indices loaded in 0.79s on startup | **PASS** | `docker logs mediscanai-backend` |
| **T2-MIG-01** | Database Migrations | Execute Alembic migrations against containerized PostgreSQL | `docker compose -f deployment/compose.yaml up -d` (via entrypoint) | 3 migrations apply cleanly; tables `users`, `analyses`, `audit_logs` created | Migrations `0001`, `0002`, `0003` applied automatically on container startup | **PASS** | `docker logs mediscanai-backend` |
| **T2-API-01** | Health & Readiness | Verify `/api/health` and decoupled `/api/ready` in `online` mode | `curl -f http://localhost/api/ready` | Returns HTTP 200 with status `"ready"` without requiring Ollama | HTTP 200: `status: "ready"`, `ollama_service: "not_required"`; 6/6 unit tests passed | **PASS** | `deployment/logs/test_health_and_readiness.log` |
| **T2-API-02** | Online Text Analysis | End-to-end analysis using Gemini/Groq inside local container stack | Automated script: register user $\to$ login $\to$ call `/api/analyze` | Returns HTTP 200 with complete clinical summary card and DB persistence | Registration: 201; Login: 200; Analyze (text-only): 200 in 31.98s; persisted in DB. (Note: Multimodal strip OCR verified separately in unit tests). | **PASS** | `deployment/logs/phase2_runtime_verification.log` |
| **T2-PERS-01** | Volume Persistence | Verify database and model cache survive container restarts | `docker compose restart postgres backend` then query database | User and analysis records intact | 2 users and 1 analysis record verified intact after container restarts | **PASS** | `deployment/logs/phase2_runtime_verification.log` |
| **T2-REV-01** | Caddy Proxy (Local) | Ingress routing and security headers over local HTTP (:80) | `curl -s -i http://localhost/api/health` | Strict security headers present; internal ports hidden | HSTS, nosniff, DENY, X-Request-ID present; ports 5432 & 8000 internal only. (Note: Public Let's Encrypt TLS requires cloud domain). | **PASS** | `deployment/logs/phase2_runtime_verification.log` |
| **T2-RES-01** | Resource Snapshot | Measure container steady-state memory consumption post-startup | `docker stats --no-stream` | Baseline memory $\le$ 3.0 GB across all containers | Backend: 1.59 GiB, Postgres: 22.5 MiB, Caddy: 21.4 MiB. Stack total: 1.64 GiB. (Point-in-time snapshot, not a concurrent stress test). | **PASS** | `deployment/logs/phase2_runtime_verification.log` |
| **T2-REG-01** | Regression Suite | Focused regression suite across OCR, pipeline, guardrails, API | `pytest tests/test_ocr.py tests/test_pipeline.py ...` | Zero regressions in core application flows | 12/12 passed in 230.33s. (Distinguished from broader 214/221 suite where 3 DB tests failed due to local DB absence, 4 required flags). | **PASS** | `deployment/logs/regression_test_suite.log` |

---

## 3. Phase 3: Planned Cloud Production Test Matrix

| Test ID | Component | Test Description | Command / Procedure | Expected Outcome | Actual Outcome | Status | Evidence / Log Reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **T3-PROV-01** | Cloud Provisioning | Oracle Cloud Ampere A1 instance boot & OS verification | `uname -m && lscpu` | Reports `aarch64` architecture, 2 OCPUs, 12 GB RAM | Deferred to Phase 3 | **NOT RUN** | Pending Phase 3 execution |
| **T3-NET-01** | Firewall & Security | UFW and Oracle Security List port validation | `nmap -Pn $SERVER_IP` | Only ports 22, 80, and 443 are open; database port 5432 is closed | Deferred to Phase 3 | **NOT RUN** | Pending Phase 3 execution |
| **T3-TLS-01** | Ingress Security | Automated Let's Encrypt TLS certificate verification | `curl -Iv https://api.yourdomain.com/api/health` | Valid HTTPS connection; HTTP 200 response | Deferred to Phase 3 | **NOT RUN** | Pending Phase 3 execution |
| **T3-E2E-01** | Cloud Multimodal | Live production symptom and medicine analysis | Automated test script against public domain | Validated analysis persisted to PostgreSQL in cloud | Deferred to Phase 3 | **NOT RUN** | Pending Phase 3 execution |
| **T3-FRONT-01** | React Integration | Live React web client connection to production API | User browser test | Dashboard loads analysis history; submits live analysis | Deferred to Phase 3 | **NOT RUN** | Pending Phase 3 execution |
| **T3-RES-01** | Reboot Resilience | Automated container restart test after VM reboot | `sudo reboot` then monitor `docker ps` | Stack recovers automatically within 60s without manual intervention | Deferred to Phase 3 | **NOT RUN** | Pending Phase 3 execution |

