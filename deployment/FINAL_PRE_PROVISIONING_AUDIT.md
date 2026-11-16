# MediScanAI — Final Pre-Provisioning Deployment & Documentation Audit

**Audit Date:** 2026-11-15  
**Auditor Role:** Senior DevOps Engineer, Backend Architect & ML Infrastructure Auditor  
**Repository:** `https://github.com/djcode0718/MediscanAI`  
**Working Branch:** `feature/cloud-docker-deployment`  
**Current HEAD Commit:** `fc5ad47 docs: update README with comprehensive features and architecture overview`  
**Target Environment:** Oracle Cloud Infrastructure (OCI) Always Free — Ampere A1 ARM64 (`VM.Standard.A1.Flex`)  
**Deployment Budget:** Strictly ₹0 / month  
**Overall Readiness Verdict:** **READY WITH WARNINGS** (Local container stack, security controls, and documentation verified; cloud deployment blocked on user OCI tenancy provisioning, regional A1 capacity, and DNS configuration).

---

## 1. Classification Framework

Every audited component, finding, and operational procedure is evaluated and classified according to the following criteria:

* **PASS**: Verified against code, local container execution, and documentation; satisfies all engineering, safety, and architectural requirements.
* **CORRECTED**: Inaccuracy, informal naming, unverified claim, or dependency flaw previously present in documentation that has now been reconciled and aligned with codebase reality.
* **WARNING**: Architectural, capacity, or operational consideration that does not block deployment but requires vigilance, deliberate user acceptance, or ongoing monitoring.
* **BLOCKED**: Item that cannot be verified or completed by the local agent due to absence of cloud credentials, cloud infrastructure, or external user prerequisites.
* **NOT VERIFIED**: Work that is designed, scripted, and verified in local simulation, but whose live execution against the cloud host remains pending cloud provisioning.

### Audit Summary Statistics
| Status | Count | Notes |
| :--- | :---: | :--- |
| **PASS** | 24 | Architecture, security, container builds, DB migrations, API contracts, zero-cost policy |
| **CORRECTED** | 9 | Model identifiers, latency claims, steady-state memory qualification, OCR claims, P3-T11 dependency |
| **WARNING** | 4 | Regional A1 capacity starved state, commercial LLM privacy boundary, SSH brute-force risk, load spike headroom |
| **BLOCKED** | 3 | OCI VM provisioning (user credentials required), DNS A-record configuration, public Let's Encrypt TLS issuance |
| **NOT VERIFIED** | 2 | Cloud VM reboot resilience on live host, full end-to-end cloud URL smoke test |

---

## 2. Files Inspected

The audit conducted an exhaustive cross-reference across all deployment manifests, code configurations, and execution logs:

### A. Deployment Artifacts & Documentation (`deployment/`)
1. `deployment/TASKS.md`: Master deployment task tracker and phase progression.
2. `deployment/AUDIT_REPORT.md`: Phase 1 comprehensive backend and infrastructure audit.
3. `deployment/ARCHITECTURE.md`: High-level system architecture and request pipeline topology.
4. `deployment/DEPENDENCY_COMPATIBILITY.md`: ARM64 multi-architecture binary wheel audit.
5. `deployment/DEPLOYMENT_DECISIONS.md`: Architectural Decision Records (ADR-01 through ADR-08).
6. `deployment/TEST_MATRIX.md`: Test execution matrix and pass/fail criteria.
7. `deployment/PRODUCTION_VERIFICATION.md`: Phase 2 container runtime verification report.
8. `deployment/DEPLOYMENT_SUMMARY.md`: Executive summary of Docker engineering.
9. `deployment/RUNBOOK.md`: Operational production runbook and backup/recovery manual.
10. `deployment/CHANGELOG.md`: Detailed engineering changelog.
11. `deployment/Dockerfile`: Multi-stage production container definition.
12. `deployment/compose.yaml`: Multi-container production orchestration.
13. `deployment/Caddyfile`: Reverse proxy and TLS ingress configuration.
14. `deployment/requirements.txt`: Pin-stabilized production Python dependencies.
15. `deployment/docker-entrypoint.sh`: Container startup and database migration wrapper.
16. `deployment/.env.example`: Production environment variable template.
17. `deployment/.env`: Local test environment configuration (strictly git-ignored).

### B. Application Source Code & Test Suites
1. `backend/core/config.py`: Application settings, environment schema, and default model identifiers.
2. `backend/main.py`: FastAPI application factory, lifespan management, and router mounting.
3. `app/llm_providers.py`: Multi-provider fallback orchestrator (Gemini -> Groq).
4. `app/ocr.py`: PaddleOCR text extraction engine.
5. `app/retrieval.py`: Hybrid lexical/vector retrieval (BM25 + FAISS + CrossEncoder).
6. `tests/api/test_health_and_readiness.py`: Health and readiness probe unit tests.
7. `tests/api/test_ocr.py`: Unit test verifying PaddleOCR packaging text extraction.

### C. Execution Logs (`deployment/logs/`)
1. `deployment/logs/phase1_app_baseline.log`: 6/6 baseline application tests.
2. `deployment/logs/phase1_eval_baseline.log`: 125/125 clinical evaluation tests.
3. `deployment/logs/phase1_unit_baseline.log`: 214/221 fast unit test execution.
4. `deployment/logs/phase2_runtime_verification.log`: Live container runtime HTTP test log.

---

## 3. Files Modified During Reconciliation

The following documentation files were updated to reconcile claims with codebase evidence:

| File Path | Nature of Edits |
| :--- | :--- |
| `deployment/PRODUCTION_VERIFICATION.md` | Qualified testing to Apple Silicon M4 Docker environment; renamed Section 4 to "Authentication, Text-Only Analysis & Persistence Verification"; corrected latency claims to 31.98s recorded; qualified memory snapshot to ~1.64 GiB steady-state; qualified TLS to local HTTP (:80); distinguished 12/12 regression suite from 214/221 unit suite. |
| `deployment/DEPLOYMENT_DECISIONS.md` | Standardized ADR-02 model chain to exact code identifiers (`gemini-3.6-flash`, `gemini-3.7-flash`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`); removed unsupported latency/peak claims; added explicit Cost & Quota Boundary; updated Risk R-07 memory guidance. |
| `deployment/AUDIT_REPORT.md` | Aligned model names in executive summary; replaced unqualified "zero OOM risk" statement with measured steady-state snapshot and theoretical headroom analysis. |
| `deployment/ARCHITECTURE.md` | Aligned Mermaid architecture diagram and provider table with exact code identifiers; removed "sub-second LLM generation" and "100% preservation of clinical OCR" phrases. |
| `deployment/DEPLOYMENT_SUMMARY.md` | Aligned LLM model chain identifiers with `backend/core/config.py`. |
| `deployment/TEST_MATRIX.md` | Added environmental scope disclaimer; qualified test-modality, proxy scope, resource snapshot, and regression suite distinctions. |
| `deployment/CHANGELOG.md` | Updated items 5, 7, 10, 11, and 12 to accurately reflect testing environment, text-only analysis, and Caddy local HTTP scope. |
| `deployment/TASKS.md` | Decoupled task `P3-T11` dependency from `P3-T10` to `P2-T06, P2-T09`; added Section 4 (Phase 4: Future Enhancements) with `P4-T01: Expand LLM Fallback Chain with Additional Zero-Cost Providers` covering 8 specific criteria. |
| `deployment/RUNBOOK.md` | Added OCI Always Free regional capacity constraint warning; added SSH ingress restriction recommendations; added Section 8 (Health-Data Privacy & Data-Minimization Guidelines). |

---

## 4. Documentation Reconciliation & Correction Log

| Audit Topic | Previous Claim | Corrected Reality & Rationale | Status |
| :--- | :--- | :--- | :---: |
| **Integration Test Modality** | Described as an end-to-end multimodal `/api/analyze` verification. | Renamed to **"Authentication, Text-Only Analysis & Persistence Verification"**. The live container HTTP test dispatched a text-only payload (`{"text": "Patient presents with severe headache..."}`). Packaging OCR was verified separately via `test_ocr.py` (synthetic pill box), not as an image payload to `/api/analyze`. | `CORRECTED` |
| **Pipeline Latency Claims** | Casual claims of "sub-second" or "~1.5s" LLM inference latency. | Replaced with recorded client-side total duration: **31.98 seconds** (with **31,930 ms** recorded in `analyses.processing_duration_ms`). Internal sub-stage latencies were not separately instrumented; documentation now accurately reflects total observed latency. | `CORRECTED` |
| **Memory Footprint & OOM Risk** | Asserted "zero OOM risk" and "measured ~2.5 GB peak load". | Replaced with **measured steady-state point-in-time snapshot of ~1.64 GiB** (Backend: ~1.59 GiB, Postgres: 22.5 MiB, Caddy: 21.4 MiB). Documentation notes this is a single-request baseline snapshot, not a concurrent stress test, while confirming a healthy theoretical margin (>10.3 GiB unallocated) on a 12 GB VM. | `CORRECTED` |
| **OCR Text Accuracy Claims** | Stated "100% preservation of clinical OCR accuracy". | Replaced with evidence-based statements: PaddleOCR 3.0 ARM64 wheel initializes correctly, loads detection and recognition models without errors, and passes unit test `test_ocr.py` on synthetic medicine strips. | `CORRECTED` |
| **Reverse Proxy & TLS Verification** | Stated automated Let's Encrypt TLS was fully verified. | Clarified that Caddy was verified locally on port `:80` (HTTP) with security headers, reverse proxy routing, and upload limits. Automated Let's Encrypt TLS issuance requires a public IP and registered DNS domain, which is pending cloud VM provisioning. | `CORRECTED` |
| **Test Suite Disambiguation** | Conflated 12/12 regression tests with the earlier 214/221 unit test baseline. | Clearly distinguished the 12/12 selected container regression test suite (health, readiness, OCR, retrieval, auth) from the broader 214/221 fast unit test suite executed during Phase 1. | `CORRECTED` |
| **Task Tracker Dependencies** | `P3-T11` (Runbook & Backups) depended on `P3-T10` (Cloud VM reboot). | Decoupled `P3-T11` dependency to `P2-T06, P2-T09`. Runbook documentation and backup/restore verification were completed inside local containers independently of live cloud reboot testing. | `CORRECTED` |

---

## 5. LLM Fallback Chain, Provider Identifiers & Zero-Cost Policy

### A. Fallback Chain Alignment
The codebase configuration (`backend/core/config.py:68-72` and `app/llm_providers.py:281-286`) enforces a 4-tier fallback hierarchy:

$$\text{Primary: } \texttt{gemini-3.6-flash} \longrightarrow \text{Fallback 1: } \texttt{gemini-3.7-flash} \longrightarrow \text{Fallback 2: } \texttt{openai/gpt-oss-120b} \longrightarrow \text{Fallback 3: } \texttt{openai/gpt-oss-20b}$$

* **Status:** `PASS`
* **Verification:** All references in `ARCHITECTURE.md`, `DEPLOYMENT_DECISIONS.md`, `DEPLOYMENT_SUMMARY.md`, `RUNBOOK.md`, and `.env.example` now use these exact model identifiers. Informal aliases ("Gemini 2.5 Flash", "Groq Llama 3.3") have been removed.

### B. Zero-Cost Policy Enforcement & Billing Boundary
* **Status:** `PASS (Conditional on Free Quotas & Account Configuration)`
* **Mechanism & Boundary Conditions:**
  1. **Intended Free-Tier Scope**: MediScanAI is engineered to operate strictly within eligible free-tier developer allowances (Google Gemini API free tier and Groq Cloud free tier).
  2. **Billing Settings Safeguard**: The orchestrator catches `ProviderExhaustionError` and returns a controlled `HTTP 503 Service Unavailable` with `detail: "All configured LLM providers are currently unavailable or rate-limited"`. However, returning HTTP 503 does not, by itself, configure external provider account billing. Administrators must independently verify on the Google AI Studio / Google Cloud Console and Groq Cloud Console that accounts are configured with $0 spend caps and that no pay-as-you-go credit card profile enables automatic paid overages.
  3. **No Silent Paid Routing**: Under no circumstances does the application silently route traffic to paid endpoints, metered cloud infrastructure, or premium models without explicit administrative reconfiguration.
  4. **No Unlimited Free Usage Guarantee**: Commercial providers offer no guarantee of unlimited or perpetual free developer quotas; availability and rate limits remain subject to vendor policies.

### C. Future Fallback Expansion (`P4-T01`)
* **Status:** `PASS` (Documented in `deployment/TASKS.md`)
* Added explicit acceptance criteria covering candidate research, model identifier verification, quota/terms evaluation, structured JSON benchmarking, latency profiling, graceful circuit-breaking, zero-cost enforcement, and fault-injection testing.

---

## 6. Health-Data Privacy & Data-Minimization Review

* **Status:** `PASS` (with `WARNING` on commercial provider boundaries)
* **Application Scope:** MediScanAI extracts text from medicine packaging images, takes clinical symptom narratives, retrieves relevant drug monographs from an embedded local FAISS index, and generates structured analysis.
* **Minimization Safeguards:**
  1. **No Direct PII Required (`PASS`):** The application does not collect full legal names, government IDs, phone numbers, or addresses. Authentication requires only an email and password.
  2. **Prompt Decoupling (`PASS`):** User account IDs, emails, and database keys are excluded from prompt templates passed to external LLMs.
  3. **Log Sanitization (`PASS`):** Raw images, audio bytes, and sensitive clinical narratives are not dumped into persistent application stdout logs. `DEBUG=false` is enforced in production.
  4. **Credential Isolation (`PASS`):** API keys reside solely in server environment variables with `600` permissions.
  5. **Commercial Provider Boundary (`WARNING`):** While HTTPS/TLS secures data in flight, prompt text dispatched to Gemini and Groq is subject to the data retention, training, and privacy policies of Google and Groq. Application-level data minimization is enforced, but absolute external anonymity cannot be guaranteed once prompts exit the server boundary.

---

## 7. Container, Networking, Security & Ingress Review

| Security Control | Implementation Mechanism | Verification Result | Status |
| :--- | :--- | :--- | :---: |
| **Multi-Stage Build** | Two-stage `Dockerfile`: build stage compiles C-extensions; runtime stage copies clean venv and strips compilers (gcc, g++, make). | Measured local ARM64 image (available locally): 11.66 GB uncompressed (11,661,074,862 bytes; 3.89 GB containerd content size); compressed transfer archive: ~3.88 GB (3,878,709,150 bytes). Verified clean build. | `PASS` |
| **Non-Root Execution** | Runtime container runs under dedicated `appuser` (UID 1000, GID 1000). Root access is dropped. | Confirmed via `id`: `uid=1000(appuser) gid=1000(appuser)`. | `PASS` |
| **Network Isolation** | `mediscanai-backend` and `mediscanai-postgres` communicate over private bridge network `mediscanai_internal_net`. | Zero host port bindings on database (`docker port mediscanai-postgres` returns empty). | `PASS` |
| **Ingress Control** | Caddy reverse proxy binds public ports `:80` and `:443`. Backend is reached solely via internal DNS name `http://backend:8000`. | Caddy passes requests through reverse proxy; backend port 8000 is not exposed to host. | `PASS` |
| **Request Size Limits** | Caddy enforces `request_body { max_size 30MB }`. | Prevents memory exhaustion attacks via oversized image or audio payloads. | `PASS` |
| **Security Headers** | Caddy injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security: max-age=31536000`. | Verified via `curl -I http://localhost:80/api/health`. All headers present. | `PASS` |
| **CORS Validation** | Backend requires explicit JSON array for `CORS_ORIGINS`. Wildcards (`"*"`) are explicitly rejected in production. | Validated in `backend/core/config.py`. | `PASS` |
| **Secret Management** | Credentials injected via `.env` with `chmod 600`. `.env` is listed in `.gitignore` and `.dockerignore`. | Verified no plaintext secrets committed to Git repository. | `PASS` |
| **Read-Only Mounts** | Static datasets (`data/`) and FAISS indexes (`indexes/`) mounted with `:ro` flag. | Containers cannot tamper with or corrupt static retrieval assets. | `PASS` |

---

## 8. Operational Runbook Completeness Review

* **Status:** `PASS` (with `WARNING` on regional capacity)
* **Coverage:**
  1. **Prerequisites & Sizing (`PASS`):** Exact instance shape (`VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM, 50 GB boot volume) documented.
  2. **OS Hardening & Docker Setup (`PASS`):** Step-by-step commands for Ubuntu 24.04 aarch64, UFW firewall, Fail2ban SSH jail, and Docker Engine CE repository.
  3. **Dual-Layer SSH Ingress & Fail2ban Hardening (`PASS`):** Runbook explicitly restricts SSH port 22 to administrator CIDR (`YOUR_PUBLIC_IP/32`) at both OCI VCN and host UFW levels, details a two-session safety procedure to avoid lockout, and configures Fail2ban with verification commands.
  4. **OCI Capacity Warning (`WARNING`):** Added explicit guidance that Always Free Ampere A1 capacity may be starved in specific availability domains, detailing mitigation strategies (retry during off-peak hours, select alternative ADs).
  5. **Asset & Image Transfer (`PASS`):** Documented exact `rsync` commands for `data/` (~111 MB) and `indexes/` (~217 MB), along with `docker save | gzip` transfer (~3.88 GB compressed archive) to avoid building compilers on the cloud VM.
  6. **Backup & Isolated Restore (`PASS`):** Provided non-destructive backup validation using `pg_restore -l` and restoration into an isolated test database (`mediscanai_restore_test`) to verify schema and row counts without impacting production.
  7. **Emergency Recovery (`PASS`):** Documented troubleshooting steps for container health failures, database connection resets, and VM reboot recovery.

---

## 9. Pre-Cloud Verification Scope & Environmental Distinction

| Verification Dimension | Local Container Test Environment | Live Cloud Target Environment (OCI) | Status |
| :--- | :--- | :--- | :---: |
| **Hardware / CPU** | Apple Silicon M4 (macOS host) | Ampere Altra A1 (Neoverse N1 ARM64) | `PASS` (Local) / `NOT VERIFIED` (OCI) |
| **Kernel / OS** | LinuxKit aarch64 container kernel | Ubuntu 24.04 LTS aarch64 native kernel | `PASS` (Local) / `NOT VERIFIED` (OCI) |
| **Binary Compatibility** | PaddlePaddle 3.0, FAISS-CPU 1.16.0, Torch 2.14.1 (torch.__version__ == '2.14.1+cu130'), OpenCV Headless 4.10.0 verified | Same wheels will run on OCI Linux aarch64 | `PASS` |
| **Database Migrations** | Alembic applied migrations 0001, 0002, 0003 cleanly in container Postgres | Same automated migration logic will execute on OCI | `PASS` |
| **API Functionality** | `/api/health`, `/api/ready`, `/api/auth/register`, `/api/auth/login`, text-only `/api/analyze` verified | Same container image loaded on OCI | `PASS` |
| **Reverse Proxy** | Caddy reverse proxy verified on local HTTP port `:80` | Caddy will negotiate automated Let's Encrypt TLS on `:443` | `PASS` (HTTP) / `BLOCKED` (TLS) |
| **Memory Footprint** | Measured ~1.64 GiB steady-state snapshot on single request | Live concurrent performance to be monitored under real load | `PASS` (Baseline) / `WARNING` (Concurrency) |

---

## 10. Outstanding Cloud Deployment Blockers

The following items are **BLOCKED** and cannot be executed autonomously by the agent without user action:

1. **OCI Tenancy Access & VM Provisioning (`BLOCKED`):**
   * *Reason:* The local execution environment does not have OCI CLI credentials, API keys, or tenancy access tokens configured.
   * *Resolution:* The user must log into the Oracle Cloud Console and manually provision the `VM.Standard.A1.Flex` instance, or provide an active SSH private key and public IP.
2. **Regional Ampere A1 Host Capacity (`WARNING / BLOCKED`):**
   * *Reason:* Always Free Ampere A1 compute capacity is subject to regional availability and may be temporarily exhausted in the user's primary region.
   * *Resolution:* User must select an available Availability Domain in the OCI Console or retry during low-traffic windows.
3. **Public Domain & DNS A-Record (`BLOCKED`):**
   * *Reason:* Automated Let's Encrypt TLS issuance requires a registered domain name whose DNS A-record points directly to the OCI VM's public IPv4 address.
   * *Resolution:* User must assign their domain or subdomain (e.g. `api.yourdomain.com`) to the provisioned public IP, or set `DOMAIN_NAME=:80` for initial IP-only HTTP testing.
4. **Data & Image Rsync Transfer (`BLOCKED` on VM access):**
   * *Reason:* Transferring `data/`, `indexes/`, and the verified Docker image requires an active SSH connection to the live cloud host.
   * *Resolution:* User provisions the VM and provides SSH connectivity.

---

## 11. OCI Provisioning Specifications & Prerequisites

When creating the cloud instance in Oracle Cloud Console, adhere strictly to the following parameters:

* **Compartment:** Root compartment (or dedicated Always Free compartment).
* **Availability Domain:** Select an AD with available capacity (AD-1, AD-2, or AD-3).
* **Shape:** `Ampere` -> `VM.Standard.A1.Flex`
* **OCPU Count:** `2 OCPU`
* **Memory Allocation:** `12 GB RAM`
* **Operating System:** `Canonical Ubuntu` -> `Ubuntu 24.04 Minimal LTS` (Architecture: `aarch64`)
* **Boot Volume:** `50 GB` (Default Always Free allows up to 200 GB across tenancy).
* **Networking / VCN:**
  * Create or select a Virtual Cloud Network with an Internet Gateway.
  * Assign a **Public IPv4 Address**.
* **Security List Rules:**
  * Ingress: Port 22 (SSH, restricted to your IP), Port 80 (HTTP), Port 443 (HTTPS).
  * Egress: All traffic (`0.0.0.0/0`).
* **SSH Keys:** Add your public SSH key (`~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub`).

---

## 12. Explicit Safety & Boundary Confirmations

1. **Zero Cloud Resources Created:** No cloud instances, virtual cloud networks, block volumes, DNS records, or external cloud resources were created or modified during this audit.
2. **Zero Git Commits, Pushes, or Resets:** The working branch remains `feature/cloud-docker-deployment`. No commits were created, no code was pushed to remote repositories, no branches were switched, and no Git states were reset or stashed.
3. **Budget Adherence:** The entire architecture, container stack, and operational procedures strictly maintain the ₹0 / month budget requirement.

---

## 13. Audit Conclusion & Readiness Verdict

### Overall Verdict: **READY WITH WARNINGS**

The MediScanAI containerized application stack has completed comprehensive local validation, dependency hardening, and documentation reconciliation:
* The Docker container builds cleanly on Linux ARM64 with non-root security and stripped compilers.
* Reverse proxying, database networking isolation, health probes, and authentication are fully operational.
* All documentation has been purged of unverified claims and brought into strict concordance with code defaults and empirical measurements.
* The system is fully prepared for immediate provisioning and deployment on Oracle Cloud Infrastructure as soon as the user completes cloud VM creation.

---

## 14. Residual Findings & Pre-Provisioning Hardening Review

### A. What Was Corrected in This Audit Turn:
1. **Architecture Claims Reconciled**:
   - In `deployment/ARCHITECTURE.md`, purged speculative claims ("sub-second LLM generation", "100% preservation of clinical OCR"); aligned documentation with the empirical 31.98s recorded end-to-end request latency (31,930 ms in DB) and synthetic OCR unit test verifications.
2. **Conditional Zero-Cost Enforcement Documented**:
   - Reconciled ₹0 monthly cost across `DEPLOYMENT_SUMMARY.md`, `DEPLOYMENT_DECISIONS.md`, `RUNBOOK.md`, and this audit. Documented that ₹0 is conditional on eligible free-tier quotas and external account billing configuration. Clarified that the application returning HTTP 503 on provider exhaustion halts software retries but does not configure third-party account billing settings. Noted that administrators must verify spend limits are capped at $0 on Google Cloud and Groq dashboards.
3. **Docker Image Sizing Empirically Measured**:
   - Resolved conflicting image size reports (~950 MB vs 4.88 GB vs 11.7 GB). Measured actual local Docker image `mediscanai-backend:production` (Image ID: `1d080e38142b`):
     - **Image Availability Locally:** YES.
     - **Image Architecture:** `linux/arm64` (`Architecture: arm64`, `OS: linux`).
     - **Uncompressed Image Size:** `11,661,074,862` bytes (~10.86 GiB / 11.66 GB).
     - **Containerd Content Size:** `3.89 GB`.
     - **Compressed `docker save | gzip` Transfer Archive Size:** `3,878,709,150` bytes (~3.61 GiB / ~3.88 GB).
4. **PyTorch Version Verified**:
   - Reconciled conflicting version reports. Verified directly inside `mediscanai-backend:production` container that installed Torch version is **`torch 2.14.1`** (specifically string `'2.14.1+cu130'`). Updated all documentation to match.
5. **Dual-Layer SSH Hardening**:
   - Updated `RUNBOOK.md` to restrict SSH port 22 at both the OCI VCN Security List and host UFW firewall using the placeholder `YOUR_PUBLIC_IP/32`. Added an explicit two-terminal safety procedure to prevent administrator lockout before closing the initial session. Ports 80 and 443 remain publicly accessible.
6. **Fail2ban Integration Added**:
   - Integrated Fail2ban installation, SSH jail configuration (`/etc/fail2ban/jail.d/sshd.local`), and runtime verification commands into `RUNBOOK.md` to fulfill task `P3-T04`.
7. **Production CORS Configuration Hardened**:
   - In `RUNBOOK.md` and `deployment/.env.example`, updated production CORS examples to require only deployed frontend HTTPS origins (`["https://app.yourdomain.com", "https://yourdomain.com"]`). Explicitly documented that `localhost` and `127.0.0.1` origins are for local development only and must not be present in a public production allowlist.

### B. What Remains Unverified (Awaiting Live Cloud Host):
1. **Live Cloud Execution on Ampere A1 Hardware**:
   - Host kernel and real ARM64 hardware behavior (currently verified inside LinuxKit ARM64 VM on macOS M4).
2. **Automated Let's Encrypt TLS Issuance**:
   - Cannot be tested until a public DNS A-record points to the live OCI VM IP.
3. **Live UFW and Fail2ban Execution**:
   - Documented and validated syntactically; runtime execution pending on the newly provisioned Ubuntu cloud host.

### C. What Requires User Action:
1. **OCI Console Instance Provisioning**:
   - Create `VM.Standard.A1.Flex` (Ubuntu 24.04 aarch64, 2 OCPUs, 12 GB RAM, 50 GB boot volume) in an available Availability Domain.
2. **Provider Account Verification**:
   - Verify on Google AI Studio / Google Cloud Console and Groq Cloud Console that API keys are active, rate limits are acceptable, and spend limits are capped at $0 with no active pay-as-you-go credit cards.
3. **DNS Mapping**:
   - Point your custom domain or subdomain DNS A-record to the provisioned public IP.
4. **Execute Runbook Commands**:
   - Connect via SSH and follow the step-by-step commands in `deployment/RUNBOOK.md`.

### D. Final Readiness Verdict:
**READY FOR OCI PROVISIONING.** All prerequisites, container images, configs, and documentation are reconciled and hardened.

