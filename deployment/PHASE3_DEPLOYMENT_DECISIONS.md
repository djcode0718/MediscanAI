# MediScanAI — Phase 3 Architectural & Deployment Decisions (ADRs)

**Status:** Approved & Implemented
**Date:** November 17, 2026
**Scope:** Phase 3 Pre-Provisioning & Docker Deployment Finalization
**Repository Branch:** `main`
**Commit Baseline:** `8751520943d64e596fe140a440eacf43a753c9d1`

---

## ADR-001: Unified Multi-Target Dockerfile vs Separate Architecture Dockerfiles

### Context
In Phase 2, an experimental CPU-only Dockerfile (`deployment/Dockerfile.cpu`) was created alongside the baseline `deployment/Dockerfile`. While `Dockerfile.cpu` successfully reduced image size from 11.66 GB to 3.85 GB, maintaining two separate Dockerfiles creates technical debt, documentation ambiguity, and configuration drift risk between staging and production environments.

### Options Considered
1. **Approach A (Maintain Dual Dockerfiles):** Keep `Dockerfile` for baseline/GPU and `Dockerfile.cpu` for ARM64 CPU.
2. **Approach B (Replace `Dockerfile` entirely with CPU version):** Permanently remove the original `Dockerfile` and rename `Dockerfile.cpu` to `Dockerfile`.
3. **Approach C (Unified Multi-Target Dockerfile with `BUILD_TARGET`):** Unify both into `deployment/Dockerfile` using Docker build argument `ARG BUILD_TARGET=cpu` (default), conditionally installing CPU PyTorch wheels while preserving a single source of truth.

### Decision
**Approach C was selected.** `deployment/Dockerfile` was refactored with `ARG BUILD_TARGET=cpu` as the default build target.

### Evidence & Rationale
- `deployment/Dockerfile` now deterministically installs `torch==2.14.1+cpu` from `https://download.pytorch.org/whl/cpu` during the builder stage.
- The resulting unified image (`mediscanai-backend:production`, ID `4ea6bb3f3e42`) is 3.86 GB uncompressed and 865 MB compressed archive, identical in footprint and behavior to the experimental CPU image.
- A single Dockerfile eliminates file drift and aligns `compose.yaml` with the canonical build target.

### Tradeoffs & Mitigations
- *Tradeoff:* Conditional logic in `Dockerfile` adds minor complexity to the builder layer.
- *Mitigation:* The build logic is isolated to a clean 5-line `if/else` block that is tested and validated on Docker Buildx.

---

## ADR-002: OpenCV Distribution Deduplication

### Context
The application relies on PaddleOCR/PaddleX for medicine packaging text detection and recognition. Previously, `deployment/requirements.txt` specified `opencv-python-headless>=4.10.0.84`, but during build, PaddleX pulled `opencv-contrib-python==4.10.0.84`. This resulted in duplicate OpenCV packages within `/opt/venv`, wasting ~180 MB of disk space and creating potential dynamic library loading conflicts.

### Options Considered
1. **Option 1 (Force `opencv-python-headless`):** Attempt to suppress PaddleX dependencies.
2. **Option 2 (Retain both):** Allow pip to install both headless and contrib variants.
3. **Option 3 (Deduplicate to `opencv-contrib-python==4.10.0.84`):** Pin `opencv-contrib-python==4.10.0.84` in `requirements.txt` to align with PaddleOCR/PaddleX requirements.

### Decision
**Option 3 was selected.** `deployment/requirements.txt` was updated to explicitly pin `opencv-contrib-python==4.10.0.84`.

### Evidence & Rationale
- PaddleX explicitly requires `opencv-contrib-python`.
- Pinning the exact version eliminates duplicate package installations in `/opt/venv`.
- Native ARM64 tests confirmed `import cv2` loads cleanly, and PaddleOCR synthetic OCR text extraction successfully identified the synthetic test label ("AMVUTTRA"). Note: Real-world OCR accuracy across varied clinical environments depends on lighting, camera angle, blur, and packaging curvature.

### Tradeoffs & Mitigations
- *Tradeoff:* `opencv-contrib-python` includes additional vision modules beyond minimal headless needs.
- *Mitigation:* Because PaddleX strictly requires these modules, this is the minimal valid footprint; duplicate wheel installation is prevented.

---

## ADR-003: Compose Fail-Fast Secret Interpolation Syntax

### Context
In earlier iterations of `deployment/compose.yaml`, fallback passwords (e.g., `POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:-mediscanai_secure_pass_2024}"`) were provided. If an administrator deployed without configuring a `.env` file, the stack would silently start with insecure, publicly known credentials.

### Options Considered
1. **Option 1 (Retain fallback defaults):** Convenient for local development, high risk in production.
2. **Option 2 (Rely on external shell pre-check scripts only):** Validates before start, but does not stop manual `docker compose up` calls.
3. **Option 3 (Docker Compose fail-fast interpolation syntax `${VAR:?error}`):** Enforce non-empty variables directly in `compose.yaml` while providing an automated `preflight-check.sh` tool.

### Decision
**Option 3 was selected.** `deployment/compose.yaml` now enforces:
- `POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be configured in deployment/.env}"`
- `JWT_SECRET_KEY: "${JWT_SECRET_KEY:?JWT_SECRET_KEY must be configured in deployment/.env}"`

### Evidence & Rationale
- When `.env` is omitted or empty, `docker compose up` halts immediately with an explicit fatal error message: `POSTGRES_PASSWORD must be configured in deployment/.env`.
- Combined with `deployment/preflight-check.sh`, this provides dual-layer security against accidental deployment with default secrets.

### Tradeoffs & Mitigations
- *Tradeoff:* Developers cannot run `docker compose up` without creating a `.env` file first.
- *Mitigation:* `deployment/.env.example` provides a clear template, and `preflight-check.sh` guides the administrator.

---

## ADR-004: Entrypoint Python Database Probe vs Shell Utilities

### Context
The backend entrypoint (`deployment/docker-entrypoint.sh`) must wait for PostgreSQL to become ready and apply Alembic migrations before starting the FastAPI server. Previously, this was implemented with an infinite shell loop using `pg_isready` and shell-interpolated database strings. This posed two risks:
1. Vulnerability to shell injection if special characters existed in database passwords.
2. Infinite blocking (zombie container) if PostgreSQL failed to start or authentication was rejected.

### Options Considered
1. **Option 1 (Third-party wait tool, e.g., `wait-for-it.sh` or `dockerize`):** Adds external binaries to the minimal production image.
2. **Option 2 (Shell `pg_isready` loop):** Only checks port reachability; does not verify database credentials or schema accessibility.
3. **Option 3 (Inline Python probe via `psycopg2` with 60s timeout):** Uses the Python virtual environment already present in the container to probe connection and authentication.

### Decision
**Option 3 was selected.** `deployment/docker-entrypoint.sh` executes an inline Python script that reads `os.environ.get('DATABASE_URL')` directly, loops up to 30 times (60 seconds), and exits with code 1 if unreachable.

### Evidence & Rationale
- Eliminates shell parsing and string interpolation of database credentials.
- Tests actual end-to-end database connectivity and credentials, not merely TCP port openness.
- Hard timeout terminates container startup with non-zero exit code if credentials fail, alerting Docker/Kubernetes health monitors immediately.
- Enforced `set -e` before `alembic upgrade head`, ensuring migration failure halts container startup.

### Tradeoffs & Mitigations
- *Tradeoff:* Slight startup overhead (~200ms) for Python process invocation.
- *Mitigation:* Negligible in production compared to container launch time.

---

## ADR-005: Safe Isolated Test-Database Verification in Restore Workflow

### Context
Disaster recovery procedures must be regularly tested to ensure backups are valid. However, testing restore procedures on a live production database risks data corruption or overwriting active clinical records.

### Options Considered
1. **Option 1 (Document manual restore only):** Leaves execution prone to operator error during outages.
2. **Option 2 (Direct restore into active database):** Destructive; cannot be used for routine verification.
3. **Option 3 (Dual-mode automated restore script with default `--test-db`):** `deployment/restore.sh` defaults to creating a temporary isolated database (`mediscanai_restore_test`), restoring the dump, verifying table row counts, and tearing down the test database.

### Decision
**Option 3 was selected.** `deployment/restore.sh` was authored with `--test-db` as the safe default mode, requiring `--force-production-restore` and an interactive confirmation string for live production restores.

### Evidence & Rationale
- Enables safe, automated routine backup verification without touching the live `mediscanai` database.
- Empirically verified on running container: restored dump, verified row counts (`users: 3`, `analyses: 1`, `audit_logs: 4`), and dropped test database cleanly.

### Tradeoffs & Mitigations
- *Tradeoff:* Requires sufficient database storage on the host to hold a second copy during verification.
- *Mitigation:* PostgreSQL dumps in custom format are compressed; row-count verification takes <3 seconds and drops the database immediately after check.

---

## ADR-006: RFC 6797 Conditional HSTS in Caddyfile for Plain HTTP Testing

### Context
In `deployment/Caddyfile`, the HSTS header (`Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`) was previously applied unconditionally. When deploying to a cloud VM for initial verification without a domain name (`DOMAIN_NAME=:80`), emitting HSTS over plain HTTP violates RFC 6797 Section 7.2 and can cause browsers to cache invalid HTTPS redirects.

### Options Considered
1. **Option 1 (Remove HSTS entirely):** Compromises production HTTPS security.
2. **Option 2 (Maintain separate Caddyfile for dev and prod):** Increases maintenance burden.
3. **Option 3 (Conditional HSTS matcher via `@https`):** Use Caddy's `@https { protocol https }` request matcher to apply HSTS strictly when requests are served over HTTPS.

### Decision
**Option 3 was selected.** `deployment/Caddyfile` was updated to wrap HSTS in `@https { protocol https }`.

### Evidence & Rationale
- Conforms strictly to RFC 6797 Section 7.2.
- Allows direct IP testing (`http://<IP>:8088` or `http://<IP>:80`) without browser redirect errors.
- Automatically enables strict HSTS once a domain name with Let's Encrypt TLS is configured.

### Tradeoffs & Mitigations
- *Tradeoff:* Requires understanding of Caddy named matchers.
- *Mitigation:* Documented clearly in `deployment/Caddyfile` comments.
