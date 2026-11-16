# MediScanAI — Production Runtime Verification & Test Evidence

**Verification Scope:** Phase 2 Local Container Stack Validation & Pre-Cloud Verification  
**Test Environment:** Apple Silicon M4 Host running Docker Desktop (LinuxKit aarch64 kernel)  
**Target Cloud VM:** Oracle Cloud Infrastructure (OCI) Ampere A1 ARM64 (`VM.Standard.A1.Flex`) — Pending Provisioning  
**Test Date:** 2026-11-15  
**Result:** **VERIFIED IN LOCAL ARM64 DOCKER ENVIRONMENT** (Cloud VM Deployment Pending)  

> **Important Environmental Scope:**  
> All tests documented below were executed on a local Apple Silicon (M4) ARM64 host using Docker Engine (`linux/arm64` container images). While this verifies Linux ARM64 binary execution, memory envelopes, and container lifecycle behavior, it is distinct from live testing on an actual Oracle Cloud Infrastructure Ampere A1 instance.

---

## 1. Phase 2 Readiness Gate Audit

| Requirement | Description | Status | Evidence Reference |
| :--- | :--- | :---: | :--- |
| **R-01** | Docker image exists for target architecture (ARM64) | **VERIFIED** | Image `mediscanai-backend:production` built for `arm64 | linux`. |
| **R-02** | Target architecture passed compatibility tests | **VERIFIED** | Native wheels verified: `paddlepaddle 3.0.0`, `torch 2.14.1`, `faiss-cpu 1.7.4`, `opencv-python-headless 4.10.0`. |
| **R-03** | PostgreSQL works with deployment configuration | **VERIFIED** | Alembic migrations `0001`, `0002`, `0003` executed cleanly in container. Tables `users`, `analyses`, `audit_logs` verified. |
| **R-04** | Datasets & FAISS indexes accounted for | **VERIFIED** | Mounted read-only into container: `../data:/app/data:ro` and `../indexes:/app/indexes:ro`. |
| **R-05** | AI pipeline initializes successfully | **VERIFIED** | Pre-warmed FAISS in 0.79s, BM25 in 65.37s, CrossEncoder in 26.31s, Faster-Whisper in 24.14s. |
| **R-06** | Operates without local Ollama service | **VERIFIED** | In `LLM_MODE=online`, `/api/ready` decouples Ollama check and returns `ollama_service: "not_required"`. |
| **R-07** | External LLM provider configuration works | **VERIFIED** | Tested live end-to-end `/api/analyze` request in online mode (HTTP 200 in 31.98s). |
| **R-08** | Container memory within target VM budget (12 GB) | **VERIFIED** | Local container stack memory measured at **1.637 GiB** during steady-state testing. |
| **R-09** | API health & readiness checks behave correctly | **VERIFIED** | `/api/health` returns `200 alive`; `/api/ready` returns `200 ready`. 6/6 unit tests passed. |
| **R-10** | Zero critical security blockers | **VERIFIED** | UID 1000 `appuser`, zero public host exposure on DB or backend, Caddy security headers active, CORS production wildcard validation. |

---

## 2. Infrastructure & Port Security Audit

```text
=== Service Status ===
NAME                  IMAGE                           COMMAND                  SERVICE    STATUS                   PORTS
mediscanai-backend    mediscanai-backend:production   "/app/docker-entrypo…"   backend    Up 4 minutes (healthy)   8000/tcp (internal)
mediscanai-caddy      caddy:2-alpine                  "caddy run --config …"   caddy      Up 6 minutes             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
mediscanai-postgres   postgres:15-alpine              "docker-entrypoint.s…"   postgres   Up 4 minutes (healthy)   5432/tcp (internal)

=== Port Isolation Verification ===
* docker port mediscanai-postgres  --> EMPTY (No public host ports exposed) [PASS]
* docker port mediscanai-backend   --> EMPTY (No public host ports exposed) [PASS]
* docker port mediscanai-caddy     --> 80/tcp -> 0.0.0.0:80, 443/tcp -> 0.0.0.0:443 [PASS]
```

---

## 3. Ingress Reverse Proxy & Security Headers (Local HTTP :80)

> **Testing Scope:**  
> The following verification confirms Caddy reverse proxy routing, request body caps, and header injection over local HTTP (`:80`). Automated TLS/HTTPS certificate provisioning via Let's Encrypt will be verified on the cloud instance once a public domain points to the VM's public IP.

HTTP Request to `http://localhost/api/health` through Caddy:
```http
HTTP/1.1 200 OK
Content-Length: 95
Content-Type: application/json
Date: Sat, 14 Nov 2026 23:04:32 GMT
Permissions-Policy: camera=(), microphone=(self), geolocation=()
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Vary: Origin
Via: 1.1 Caddy
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-Request-Id: f7bf7a181de24907

{"status":"alive","app":"MediScanAI","environment":"production","timestamp":1794697472.4056385}
```

HTTP Request to `http://localhost/api/ready` through Caddy:
```http
HTTP/1.1 200 OK
Content-Length: 210
Content-Type: application/json
Date: Sat, 14 Nov 2026 23:04:32 GMT
Permissions-Policy: camera=(), microphone=(self), geolocation=()
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Vary: Origin
Via: 1.1 Caddy
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-Request-Id: 4e22858abb784073

{"status":"ready","app":"MediScanAI","environment":"production","components":{"database":"connected","models_loaded":"ready","ollama_service":"not_required"},"concurrency":{"active_slots":0,"max_concurrent":2}}
```

---

## 4. Authentication, Text-Only Analysis & Persistence Verification

> **Modality & Testing Scope Notice:**  
> The HTTP integration tests below exercised user authentication and a **text-only** clinical analysis request (`POST /api/analyze`) submitted without packaging image or audio payloads.  
> Medicine strip OCR functionality was tested separately via unit test `tests/test_ocr.py` (synthetic pill box text extraction) and verified headless Python module imports (`cv2`, `paddleocr`). Audio speech-to-text transcription was validated via unit tests and container import of `faster_whisper`. The recorded API integration test is strictly a text-only workflow and must not be described as a full multimodal image+audio run.

### Step 1: User Registration (`POST /api/auth/register`)
* **Request Payload:** `{"email": "cloud_test_1794697119@mediscan.ai", "password": "SecurePassword123!", "full_name": "Cloud Docker Test User"}`
* **Response Status:** `201 Created`
* **Response Body:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 2,
      "email": "cloud_test_1794697119@mediscan.ai",
      "full_name": "Cloud Docker Test User",
      "is_active": true,
      "is_superuser": false,
      "created_at": "2026-11-14T22:58:39.990502Z"
    }
  }
  ```

### Step 2: User Login (`POST /api/auth/login`)
* **Request Payload:** `{"email": "cloud_test_1794697119@mediscan.ai", "password": "SecurePassword123!"}`
* **Response Status:** `200 OK`
* **JWT Access Token Issued:** Confirmed valid HS256 signature, 24-hour expiration.

### Step 3: Online Text-Only Analysis Request Execution (`POST /api/analyze`)

> **Note on Modality Scope:**  
> This specific end-to-end integration test executed a text-only clinical symptom payload without an uploaded image or audio file. Multimodal packaging OCR was verified separately via `tests/test_ocr.py` (synthetic pill box extraction) and direct container module import of `paddleocr` / `cv2`.

* **Request Payload:** `{"text": "Patient presents with severe headache, fever and sensitivity to light. Previous medications include Paracetamol."}`
* **Header:** `Authorization: Bearer <TOKEN>`
* **Response Status:** `200 OK`
* **Observed Latency:** Total client-observed request latency was `31.98s` (backend recorded `31,930 ms` total processing duration in PostgreSQL `analyses.processing_duration_ms`). Individual sub-stage latencies (retrieval vs. reranking vs. online LLM generation) were not separately isolated in the client test output.
* **Response Verdict:**
  > *"Based on the information provided, the medicine identified from the package, which appears to be Unspecified (No image provided), is not suitable for treating your symptoms of severe headache, fever, and sensitivity to light."*

### Step 4: Database Persistence Verification (PostgreSQL)
Querying PostgreSQL container directly:
```sql
SELECT id, user_id, modality, status, verdict, processing_duration_ms, created_at FROM analyses;
```
Result:
```text
 id | user_id | modality |  status   | verdict                                                     | processing_duration_ms | created_at
----+---------+----------+-----------+-------------------------------------------------------------+------------------------+-------------------------------
  1 |       2 | text     | completed | Based on the information provided, the medicine identified...|                  31930 | 2026-11-14 22:58:40.381025+00
```

---

## 5. Storage Persistence Across Restarts

1. Executed container restart: `docker compose restart postgres backend`
2. Queried database row counts post-restart:
   ```text
    count (users)
   ---------------
                2
    count (analyses)
   ---------------
                1
   ```
3. **Conclusion:** Named volume `mediscanai_postgres_data` preserves relational data without loss across container restarts.

---

## 6. Emergency Guardrail Verification

Executed `pytest tests/integration/test_emergency_guardrail_integration.py`:
* **Total Tests:** 23
* **Passed:** 23
* **Execution Time:** 0.17s
* **Coverage:** Validates acute emergency symptom interception (stroke, acute coronary syndrome, anaphylaxis, pulmonary embolism), fast-path routing, and audit logging.

---

## 7. Resource Consumption Snapshot

> **Measurement Scope:**  
> The figures below represent a point-in-time steady-state snapshot captured via `docker stats --no-stream` immediately after container startup, model pre-warming (FAISS, BM25, CrossEncoder, Whisper), and processing a single analysis request. This demonstrates baseline runtime viability, but is not a concurrent stress test or peak capacity benchmark.

* **`mediscanai-backend`:** 1.593 GiB (39.8% of 4.0 GiB container limit)
* **`mediscanai-postgres`:** 22.47 MiB (2.19% of 1.0 GiB container limit)
* **`mediscanai-caddy`:** 21.40 MiB (8.36% of 256.0 MiB container limit)
* **Total Stack RAM:** **1.637 GiB**
* **Target VM (12 GB RAM) Headroom:** **~10.36 GiB (86.3% unallocated under single-request load)**

---

## 8. Host Regression Verification

Executed focused regression test suite on host Python environment:
```text
tests/test_ocr.py .                                                      [  8%]
tests/test_pipeline.py ..                                                [ 25%]
tests/test_no_benchmark_leakage.py .                                     [ 33%]
tests/unit/test_crossfield_guard.py ..                                   [ 50%]
tests/api/test_health_and_readiness.py ......                            [100%]

======================== 12 passed in 230.33s (0:03:50) ========================
```

> **Distinction from Phase 1 Baseline:**  
> This focused 12-test suite covers core OCR, RAG retrieval pipeline, benchmark leakage prevention, crossfield guard logic, and decoupled health/readiness endpoints. It is distinct from the earlier broader 214/221 fast test suite, where 3 database tests failed due to the absence of a local PostgreSQL daemon on host port 5432, and 4 evidence-hygiene tests require explicit feature flags (`SANITIZER_A61=true`).

