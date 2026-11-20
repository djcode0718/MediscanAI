# MediScanAI — Phase 3 Final Evidence Reconciliation & Commit Readiness Audit

**Document Status:** Final Audit Complete
**Date:** November 17, 2026
**Auditor:** Principal Docker Infrastructure Engineer, ML Runtime Specialist & SRE
**Working Branch:** `main`
**Baseline Git Commit:** `8751520943d64e596fe140a440eacf43a753c9d1`
**Target Infrastructure:** Oracle Cloud Infrastructure (OCI) Always Free — Ampere A1 ARM64 (`VM.Standard.A1.Flex`)
**Instance Sizing:** 2 OCPUs, 12 GB RAM, 50 GB Boot Volume (Strictly ₹0 / month)

---

## 1. Executive Summary

This final evidence reconciliation and commit readiness audit validates the complete set of infrastructure modifications, runtime scripts, and documentation deliverables produced during Phase 3 pre-provisioning engineering.

### Audit Summary:
1. **Safety Boundary Adherence:** Strictly pre-provisioning. Zero OCI cloud resources were created; zero cloud charges were incurred; zero git staging, commits, or pushes were performed.
2. **Code & Infrastructure Hardening:** Docker build paths have been unified (Approach C), compose secrets converted to fail-fast syntax, database startup entrypoint decoupled from shell interpolation with strict timeouts, automated backup/restore scripts tested with exit cleanup traps, and Caddy ingress aligned with RFC 6797.
3. **Evidence Reconciliation:** Reconciled historical task entries, memory measurements (Phase 2 single-request baseline ~1.64 GiB vs Phase 3A full multimodal pipeline peak ~2.76 GB), and itemized the 50 GB boot volume storage engineering budget (steady-state estimate ~13.38 GB, temporary transfer archive ~0.87 GB, yielding an estimated peak deployment footprint of ~14.25 GB [~13.27 GiB] with ~35.75 GB [~33.29 GiB] projected free space, to be verified on the provisioned VM via `df -h /`).
4. **Disaster Recovery & Off-Host Strategy:** Local backup/restore routines verified. Clarified off-host disaster recovery boundaries: local Mac rsync pulls protect against VM loss only after a successful transfer; a sleeping or offline Mac cannot run scheduled jobs. Recommended macOS `launchd` with failure logging and periodic restore verification; confirmed strictly ₹0 cost without third-party cloud storage.
5. **Quality & Claim Audit:** All unsupported assertions (e.g., synthetic OCR accuracy claims, absolute stability guarantees) have been qualified. `git diff --check` passes with zero errors, and all 7 untracked files have been independently audited for syntax, whitespace, and secrets.
6. **Final Recommendation:** **READY TO COMMIT**.

---

## 2. Actual Git State & Working Tree Audit

### A. Git Inspection Outputs
- **`git branch --show-current`:** `main`
- **`git rev-parse HEAD`:** `8751520943d64e596fe140a440eacf43a753c9d1`
- **`git rev-parse origin/main`:** `8751520943d64e596fe140a440eacf43a753c9d1` (Synchronized, ahead 0, behind 0)
- **`git diff --check`:** Clean (0 whitespace warnings, 0 syntax errors)
- **Tracked Markdown Files:** 28 currently tracked in git (`git ls-files '*.md' | wc -l`). Adding the 4 Phase 3 documentation deliverables will bring the total to 32. (Note: 32 is above the preferred target range of 25–30, but remains below the repository maximum limit of 40; it is not described as within the preferred range).

### B. Tracked Files Modified (8 Files)
1. `deployment/Dockerfile`: Multi-target build with `ARG BUILD_TARGET=cpu` (default), pre-installing CPU PyTorch wheels.
2. `deployment/requirements.txt`: Pinned `opencv-contrib-python==4.10.0.84`, eliminating dual-OpenCV installation.
3. `deployment/compose.yaml`: Implemented fail-fast `${VAR:?error}` secret syntax; passed `BUILD_TARGET: cpu`.
4. `deployment/docker-entrypoint.sh`: Replaced shell DB check with safe Python probe, added 60s timeout (exit 1), enforced `set -e` on migrations, masked secret output.
5. `deployment/Caddyfile`: Added `@https { protocol https }` matcher for HSTS to comply with RFC 6797.
6. `deployment/RUNBOOK.md`: Reconciled image size (3.86 GB / 865 MB archive), transfer manifests, preflight checks, and backup/restore scripts.
7. `deployment/DEPLOYMENT_SUMMARY.md`: Reconciled Git baseline (`main` @ `8751520`), unified build details, and memory profiling figures.
8. `deployment/TASKS.md`: Labeled historical Phase 1 and 2 entries clearly; recorded Phase 3A completion and Phase 3B pending status.

### C. Untracked Files (7 Files)
1. `deployment/preflight-check.sh`: Automated configuration, secret, permission, and asset validation tool.
2. `deployment/backup.sh`: Automated PostgreSQL dump, `.env`, and Caddy cert backup script with retention pruning.
3. `deployment/restore.sh`: Safe restore tool with isolated test-database verification and production safeguards.
4. `deployment/PHASE3_PRE_PROVISIONING_AUDIT.md`: Complete Phase 3 pre-provisioning engineering audit report.
5. `deployment/PHASE3_DEPLOYMENT_DECISIONS.md`: 6 Architectural Decision Records (ADR-001 through ADR-006).
6. `deployment/OCI_PROVISIONING_CHECKLIST.md`: Step-by-step operational checklist for OCI console and host setup.
7. `deployment/PHASE3_FINAL_COMMIT_READINESS.md`: This final audit and commit readiness verification report.

### D. Credential & Hygiene Verification
- No secrets, tokens, private keys, or passwords exist in tracked or staged files.
- `deployment/.env` is ignored by `.gitignore` and has permissions 600.
- All deployment scripts use environment variables or prompted inputs.

### E. Independent Inspection of Untracked Files (7 Files)
Because `git diff --check` only inspects tracked modifications, all seven untracked files were independently validated using dedicated tooling:
1. **Shell Syntax Inspection (`bash -n`):**
   - `deployment/preflight-check.sh`: Passed (0 syntax errors).
   - `deployment/backup.sh`: Passed (0 syntax errors).
   - `deployment/restore.sh`: Passed (0 syntax errors).
2. **Whitespace & File Hygiene Audit (Python File Scanner):**
   - Scanned all 7 untracked files for carriage returns (`\r`), trailing whitespace, and missing EOF newlines.
   - Result: All 7 files passed cleanly (0 carriage returns, 0 trailing whitespace lines, 100% valid EOF newlines).
3. **Secret Pattern Scanning (Automated Regex Scan):**
   - Scanned all 8 modified tracked files and all 7 untracked files against patterns for Google API keys (`AIza...`), Groq API keys (`gsk_...`), private keys (`-----BEGIN PRIVATE KEY-----`), and hardcoded password strings.
   - Result: Passed with zero actual secrets, keys, or passwords detected.

---

## 3. Code & Infrastructure Changes Reviewed

| File | Subsystem | Nature of Change | Behavior & Security Impact |
| :--- | :--- | :--- | :--- |
| `deployment/Dockerfile` | Build Infrastructure | Added `ARG BUILD_TARGET=cpu` and conditional CPU PyTorch wheel pre-install | Unifies CPU and GPU build paths into a single source of truth; builds 3.86 GB ARM64 production image (`4ea6bb3f3e42`). |
| `deployment/requirements.txt` | Python Dependencies | Pinned `opencv-contrib-python==4.10.0.84` | Satisfies PaddleOCR/PaddleX requirements; eliminates conflicting `opencv-python-headless` package (~180 MB saved). |
| `deployment/compose.yaml` | Container Orchestration | Added `${VAR:?error}` syntax for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` | Fails fast immediately if `.env` is absent or unset; prevents silent startup with default credentials. |
| `deployment/docker-entrypoint.sh` | Container Lifecycle | Python `DATABASE_URL` probe, 60s timeout, migration abort (`set -e`) | Eliminates shell injection vulnerability; terminates container with exit 1 on DB failure; masks credentials from logs. |
| `deployment/Caddyfile` | Ingress & TLS | Conditional HSTS via `@https { protocol https }` | Prevents RFC 6797 violation during plain-HTTP direct IP testing (`:80`); automatically applies HSTS when domain TLS is enabled. |
| `deployment/preflight-check.sh` | Operations Tooling | Standalone preflight gating script | Validates `.env` permissions (600), password/JWT entropy, online LLM keys, and data mount paths; zero secret leakage to stdout. |
| `deployment/backup.sh` | Disaster Recovery | Automated custom-format dump, config, TLS certs, retention pruning | Dumps DB (`pg_dump -Fc`), enforces 600 permissions, prunes backups older than N days, cleans container `/tmp` via exit trap. |
| `deployment/restore.sh` | Disaster Recovery | Dual-mode restore tool with test-db validation | Defaults to `--test-db` mode (restores into `mediscanai_restore_test`, counts rows, drops DB); requires confirmation for live DB. |

---

## 4. Documentation Discrepancies Found and Corrected

1. **`deployment/TASKS.md`:**
   - *Discrepancy:* Historical tasks P1-T01, P2-T02, P2-T05, and P2-T13 described superseded configurations (old branch `feature/cloud-docker-deployment`, `opencv-python-headless`, 11.66 GB image, separate `Dockerfile.cpu`).
   - *Correction:* Labeled these entries explicitly as `[Historical Phase 1]` or `[Historical Phase 2]` and added clear annotations pointing to their Phase 3A consolidations without erasing historical audit records.
2. **`deployment/DEPLOYMENT_SUMMARY.md`:**
   - *Discrepancy:* Referenced old branch `feature/cloud-docker-deployment` and commit `fc5ad47`; claimed backend image size was 3.85 GB instead of 3.86 GB (unified build); contained trailing whitespace flagged by `git diff --check`.
   - *Correction:* Updated branch to `main`, commit to `8751520`, image size to 3.86 GB (`4ea6bb3f3e42`), removed trailing whitespace, and reconciled runtime memory figures.
3. **`deployment/RUNBOOK.md`:**
   - *Discrepancy:* Stated transfer image size was 11.66 GB / ~3.88 GB compressed archive; omitted new deployment scripts (`preflight-check.sh`, `backup.sh`, `restore.sh`); contained an unqualified "guaranteeing zero impact" claim.
   - *Correction:* Updated transfer instructions to 865 MB archive, added script transfers, added preflight check execution step, and qualified the database impact statement.
4. **Claims & Terminology Across Deliverables:**
   - *Discrepancy:* Statements claiming "100% OCR accuracy", "guaranteeing 100% stable execution", and unconditioned "₹0 cost".
   - *Correction:* Qualified OCR accuracy as verified on synthetic test labels (noting clinical variance with lighting/curvature); rephrased OpenMP stability to reflect elimination of observed segfaults; reinforced that ₹0 cost depends on active free-tier developer quotas and absence of paid auto-billing profiles.

---

## 5. Resource and Storage Capacity Budget

### A. Memory Reconciliation Across Project Records

| Measured Figure | Scope / Subsystem | Load Condition | Source Evidence | Context & Reconciliation |
| :--- | :--- | :--- | :--- | :--- |
| **~1.48 GB** | Backend container only | Concurrent multimodal analysis (OCR + FAISS + LLM) | Phase 2 load profiling (`CHANGELOG.md:155`) | Peak RSS of backend before CrossEncoder model was loaded into memory. |
| **~1.59 GiB** | Backend container only | Point-in-time snapshot post-startup + 1 request | `phase2_runtime_verification.log:50` | `docker stats` snapshot: `1.593GiB / 4GiB` (39.8% of container limit). |
| **~1.64 GiB** | Complete 3-container stack | Baseline single-request snapshot | `TEST_MATRIX.md:53`, `CHANGELOG.md:101` | Sum of Backend (1.593 GiB) + Postgres (22.5 MiB) + Caddy (21.4 MiB) in Phase 2. |
| **~2.76 GB** | Complete 3-container stack | Peak load under full multimodal pipeline | Phase 3A local Docker validation (`PHASE3_PRE_PROVISIONING_AUDIT.md`) | Peak Docker memory with PaddleOCR, Faster-Whisper, and heavy CrossEncoder (`ms-marco-MiniLM-L-6-v2`) active concurrently (Backend: 2.72 GB, Postgres: 48.2 MB, Caddy: 18.5 MB). |

**Conclusion:** The stack requires **~2.76 GB peak RAM**, comfortably within the **12 GB RAM** allocated on the OCI Ampere A1 instance (>9.2 GB unallocated headroom).

---

### B. Storage Capacity Engineering Budget for 50 GB OCI Boot Volume (Pre-Provisioning Estimate)

> [!NOTE]
> **Evidence Classification & Scope**:
> This storage capacity model is a **pre-provisioning engineering estimate** combining empirical local container measurements with operational assumptions for host-level dependencies.
> **Actual disk sufficiency on the OCI host has not been verified on live cloud infrastructure** and must be empirically validated upon provisioning the cloud VM using `df -h /`.
> The nominal 50 GB boot volume is specified in decimal units ($50 \times 10^9$ bytes), which equates to approximately **46.57 GiB** in binary units ($50 \times 10^9 / 1024^3$). This conversion is purely a unit distinction (decimal vs binary), not filesystem overhead. Actual usable filesystem capacity on `/` depends on disk partitioning (such as EFI `/boot/efi` allocations), filesystem metadata structures (ext4 inode tables and journal), and reserved root blocks (default 5% on ext4), and must be measured after OCI provisioning.
> The 10 GB alert threshold is a **proposed operational guideline**, not a currently active or tested monitoring mechanism.

| Storage Component | Estimated Footprint | Evidence Classification | Measurement Basis & Assumptions |
| :--- | :---: | :---: | :--- |
| **Ubuntu 24.04 LTS Minimal OS** | 3.00 GB | **ESTIMATE** | Canonical minimal rootfs and kernel |
| **System Packages & Docker Engine** | 1.00 GB | **ESTIMATE** | APT packages (`docker-ce`, `containerd`, `ufw`, `fail2ban`) |
| **Production Docker Backend Image** | 3.86 GB | **MEASURED** | `docker inspect mediscanai-backend:production` (`4ea6bb3f3e42`) |
| **Supporting Docker Images** | 0.43 GB | **MEASURED** | `postgres:15-alpine` (379 MB) + `caddy:2-alpine` (46 MB) |
| **Host Datasets & FAISS Indexes** | 0.33 GB | **MEASURED** | Host filesystem `du -sh` (`data/`: 111 MB, `indexes/`: 217 MB) |
| **Model Weights Cache (`~/.cache`)** | 0.75 GB | **ESTIMATE** | PaddleOCR (~150MB), Whisper base (~145MB), CrossEncoder (~450MB) |
| **PostgreSQL Persistent Volume** | 1.50 GB | **ASSUMPTION / ESTIMATE** | Initial empty schema (~40MB) + projected operational growth |
| **Caddy TLS Data & Certificates** | 0.01 GB | **ESTIMATE** | ACME account keys and certificates in named volume |
| **System & Container Logs** | 1.50 GB | **POLICY ASSUMPTION** | Linux `logrotate` and Docker json-file log size caps |
| **Local Rolling Backups (14-Day)** | 1.00 GB | **POLICY ASSUMPTION** | 14 rolling custom-format dumps pruned by `backup.sh` |
| **Estimated Steady-State Usage** | **~13.38 GB** | **ENGINEERING ESTIMATE** | Sum of steady-state components (~12.46 GiB) |
| **Temporary Image Transfer Archive** | 0.87 GB | **MEASURED** | `ls -lh mediscanai-backend-production-arm64.tar.gz` (865 MB / ~0.81 GiB) |
| **Peak Estimated Deployment Footprint** | **~14.25 GB** | **ENGINEERING ESTIMATE** | **Transient peak:** Steady-state (~13.38 GB) + temporary archive (0.87 GB) |
| **Nominal OCI Boot Volume Size** | **50.00 GB (~46.57 GiB)** | **SPECIFICATION** | Decimal 50 GB = ~46.57 binary GiB (unit conversion, not filesystem overhead) |
| **Projected Free Disk Space (Estimated)** | **~35.75 GB (~33.29 GiB)** | **ENGINEERING ESTIMATE** | Projected free space on `/` (pre-provisioning estimate; to be empirically measured via `df -h /`) |
| **Proposed Operational Alert Threshold** | **10.00 GB (~9.31 GiB)** | **PROPOSED THRESHOLD** | Operational recommendation (trigger cleanup if free space < 20%) |

**Storage Budget Summary:** The engineering estimate indicates that the 50 GB Always Free boot volume provides substantial projected headroom (~35.75 GB / ~33.29 GiB free). Actual disk capacity and usable space must be verified on the provisioned host using `df -h /`.

---

## 6. Backup, Restoration & Disaster Recovery Assessment

### A. Technical Assessment of Tooling
1. **`backup.sh`:**
   - Dumps PostgreSQL database using custom format (`pg_dump -Fc`), ensuring compression and fast selective restores.
   - Preserves `deployment/.env` and Caddy TLS certificates.
   - Enforces `chmod 700` on backup directories and `chmod 600` on archives.
   - Includes an `EXIT` trap to clean `/tmp/backup.dump` inside the container if the script fails.
   - Implements automated retention pruning when a retention period (e.g., 14 days) is specified.
2. **`restore.sh`:**
   - Defaults to `--test-db` mode: Creates an isolated temporary database `mediscanai_restore_test`, restores the dump, logs table row counts (`users`, `analyses`, `audit_logs`), and drops the test database.
   - Includes an `EXIT` trap to drop the test database and clean container temp files even if verification fails.
   - Safeguards live database restores (`--force-production-restore`) by requiring explicit typing of `RESTORE_PRODUCTION` or `RESTORE-PRODUCTION`.

### B. Off-Host Disaster Recovery Boundary & Explicit Limitations
- **Local vs Host Loss:** Local backups protect against application errors, failed migrations, or database corruption, but **do not protect against termination, volume failure, or total loss of the cloud VM itself**.
- **Conditional Transfer Protection:** Pulling backups off-host to the local administrative Mac protects against VM loss **only after a transfer successfully completes**.
- **Mac Sleep & Disconnect Limitations:** A local Mac that is asleep, powered off, or disconnected from the network **cannot run scheduled synchronization jobs**. Therefore, continuous disaster recovery cannot be guaranteed by client-side pulls alone.
- **Recommended Scheduling via `launchd`:** Rather than simple cron, configure a macOS `launchd` LaunchAgent (`~/Library/LaunchAgents/com.mediscanai.backupsync.plist`) with dedicated failure logging (`StandardErrorPath`), as `launchd` will automatically execute missed jobs upon system wake.
- **Periodic Verification Requirement:** Transferred backups must be periodically tested using `./restore.sh <dump> --test-db` on the local machine against a local Docker container to verify dump integrity.
- **Strictly ₹0 Cost Policy:** Consistent with project budget constraints, **do not configure third-party cloud storage** (e.g. AWS S3, Google Cloud Storage, or paid OCI tiers) to eliminate unexpected recurring billing exposure.

---

## 7. OCI Provisioning Checklist Safety & Validation Review

The checklist (`deployment/OCI_PROVISIONING_CHECKLIST.md`) was reviewed against repository structure and deployment commands:
1. **SSH Lockout Safeguards:** Explicitly instructs administrator to leave the initial SSH session open while testing UFW rules in a second independent terminal window.
2. **Network Security:** Restricts SSH ingress (Port 22) to the administrator's `/32` public IPv4 address at both the OCI VCN Security List and host UFW firewall levels. Ports 80 and 443 are opened publicly for Caddy reverse proxy ingress.
3. **Docker Permissions:** Includes `newgrp docker` immediately after `usermod -aG docker ubuntu` to ensure subsequent commands do not fail with socket permission errors.
4. **Volume Mount Alignments:** Verifies that directory creation (`~/mediscanai/data` and `~/mediscanai/indexes`) matches the relative paths in `deployment/compose.yaml` (`../data` and `../indexes`).
5. **Zero-Billing Protections:** Specifies `VM.Standard.A1.Flex` with 2 OCPUs, 12 GB RAM, and 50 GB boot volume, which falls completely within the Always Free tier limits (4 OCPUs, 24 GB RAM, 200 GB volume).

---

## 8. Remaining Findings Inventory

| Finding ID | Severity | Description | Current Status | Action Required |
| :--- | :---: | :--- | :---: | :--- |
| **F-01** | P0 | Dual Dockerfiles & colliding OpenCV packages | **RESOLVED** | Unified in `deployment/Dockerfile` (`BUILD_TARGET=cpu`); pinned `opencv-contrib-python`. |
| **F-02** | P0 | Default passwords in `compose.yaml` | **RESOLVED** | Replaced with fail-fast `${VAR:?error}` interpolation. |
| **F-03** | P0 | Unsafe entrypoint wait loop & migration aborts | **RESOLVED** | Refactored with Python DB probe, 60s timeout (exit 1), and `set -e`. |
| **F-04** | P1 | OCI VM Provisioning | **NEEDS USER ACTION** | User must log into OCI Console to provision `VM.Standard.A1.Flex` instance. |
| **F-05** | P1 | Ingress Security List Configuration | **NEEDS USER ACTION** | User must configure ports 22 (Admin IP), 80, 443 in OCI VCN. |
| **F-06** | P2 | Custom Domain Mapping & Public TLS | **NEEDS USER ACTION** | User must point DNS A-record to VM IP for automated Let's Encrypt TLS. (Plain HTTP `:80` works immediately for initial testing). |

---

## 9. Proposed Atomic Git Commit Breakdown

The working tree changes are split into two clean, self-contained atomic commits:

### Commit 1: Infrastructure & Runtime Hardening
```bash
git add \
  deployment/Dockerfile \
  deployment/requirements.txt \
  deployment/compose.yaml \
  deployment/docker-entrypoint.sh \
  deployment/Caddyfile \
  deployment/preflight-check.sh \
  deployment/backup.sh \
  deployment/restore.sh

git commit -m "fix(deployment): unify ARM64 CPU build, harden compose secrets and entrypoint lifecycle"
```

### Commit 2: Audit Deliverables & Documentation Reconciliation
```bash
git add \
  deployment/PHASE3_PRE_PROVISIONING_AUDIT.md \
  deployment/PHASE3_DEPLOYMENT_DECISIONS.md \
  deployment/OCI_PROVISIONING_CHECKLIST.md \
  deployment/PHASE3_FINAL_COMMIT_READINESS.md \
  deployment/RUNBOOK.md \
  deployment/DEPLOYMENT_SUMMARY.md \
  deployment/TASKS.md

git commit -m "docs(deployment): add Phase 3 pre-provisioning audit, ADRs, OCI checklist, and reconciled runbook"
```

---

## 10. Final Recommendation: READY TO COMMIT

The repository is in a stable, verified, and consistent state:
- All infrastructure code, build files, and runtime scripts have been tested and verified locally.
- All documentation and task records have been reconciled with actual repository code and empirical measurements.
- The 50 GB OCI boot volume storage budget has been modeled with ~35.75 GB (~33.29 GiB) of projected headroom (to be empirically validated upon VM provisioning via `df -h /`).
- `git diff --check` passes cleanly with zero warnings or errors on tracked files.
- All 7 untracked deployment files have been independently audited for shell syntax (`bash -n`), whitespace, and secrets with zero issues found.
- Zero secrets or unintended files are present.

**Recommendation:** **READY TO COMMIT** upon user authorization.
