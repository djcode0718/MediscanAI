# MediScanAI — Phase 6.5 Formal Closure & Production Operations Verification

**Document Status:** Complete & Verified  
**Date:** November 20, 2026  
**Target Platform:** Apple MacBook Air M4 (16 GB Unified Memory, 10-core CPU, macOS Sequoia 15.x)  
**Host Role:** Local Development Workstation & Persistent Production Server  
**Architecture:** Apple Silicon ARM64 (`linux/arm64`)  
**Infrastructure Cost:** ₹0 / month (Local zero-cloud architecture)  
**Pull Request:** [GitHub PR #2](https://github.com/djcode0718/MediscanAI/pull/2) (`feat: complete Phase 6.5 CI/CD and production operations`)  
**Target Branch:** `main` (Branch under review: `feat/mediscanai-cicd-operations`)

---

## 1. Executive Summary

Phase 6.5 establishes an automated, production-grade CI/CD and operations infrastructure for MediScanAI without introducing ongoing cloud hosting fees. The existing backend (FastAPI, PaddleOCR, FAISS, Graph RAG, PostgreSQL), the Vite/React frontend, and the native SwiftUI iOS application continue operating with full backward compatibility and zero architectural regressions.

### Core Guarantees Verified

1. **Zero Data Loss:** Named PostgreSQL volume `mediscanai_postgres_data` and AI model cache `mediscanai_model_cache` are permanently protected against Docker pruning, down-scaling, or maintenance cleanup.
2. **Immutable Deployments & Dual Rollback:** Every deployment tags immutable image IDs and records provenance. Automated rollbacks retain the active image and the two preceding known-good images.
3. **Exact Docker Image Ownership:** Docker image pruning strictly targets verified MediScanAI repositories (`mediscanai-backend`, `ghcr.io/djcode0718/mediscanai-backend`). Substring matching is disallowed, and unrelated third-party Docker projects on the workstation are completely isolated.
4. **Guaranteed Free Disk Headroom:** SSD utilization on `/System/Volumes/Data` is strictly governed. Deployments require at least 15 GiB absolute free headroom and are blocked at $\ge 90\%$ storage utilization.
5. **Private, Encrypted Remote Delivery:** GitHub Actions deploys via an ephemeral Tailscale mesh network (`tag:ci-cd`) authenticated directly to the host's private IP, with pinned Ed25519 host keys (`StrictHostKeyChecking=yes`). Zero inbound public ports are exposed.

---

## 2. Delivered Scope & Commit History

Phase 6.5 implementation was developed and committed on branch `feat/mediscanai-cicd-operations` across atomic, logical Conventional Commits:

| Commit | Scope | Description |
| :--- | :--- | :--- |
| `a9af9ac` | `fix(ops)` | Enforce exact MediScanAI image ownership and pre-removal recheck |
| `ea015e8` | `test(ops)` | Cover exact Docker ownership, malformed history, and force-mode safety |
| `8999f63` | `docs(ops)` | Document exact Docker image ownership and safety policies |
| `db5cfd2` | `fix(ci)` | Add maintenance safety tests and resilient Xcode simulator selection |
| `bb53bb7` | `fix(ci)` | Update macOS runner from retired macos-14 to supported macos-15 |
| `cc98ea3` | `fix(db)` | Support dialect-aware connection pooling for SQLite engines in CI |
| `be69e7c` | `fix(ci)` | Handle missing offline spellcheck dictionary and fix iOS simulator destination |
| `5052e6f` | `fix(ci)` | Robust iOS destination ID extraction and isolate unit test retrievers |
| `dc806e2` | `fix(ci)` | Dynamically select Xcode with available iOS simulator runtime |
| `4436c65` | `fix(ci)` | Quote destination argument to prevent bash whitespace splitting in xcodebuild |

---

## 3. Operational Infrastructure Components

### 3.1 Operations & Maintenance Scripts (`deployment/scripts/`)

All scripts include `set -eo pipefail`, defensive argument validation, and full execution logging:

- **`deploy.sh`**: Production deployment script. Performs pre-flight disk headroom checks, creates pre-deployment PostgreSQL safety backups, pulls immutable GHCR images, performs atomic container recreation preserving volumes, and executes post-deployment health probing with automated rollback on failure.
- **`rollback.sh`**: Reads `deployment/.deployment_history` and instantly restores the previous known-good Docker image with zero data loss.
- **`health-check.sh`**: Queries `/api/health` and `/api/ready` with retries and exponential backoff.
- **`backup-postgres.sh`**: Generates gzip-compressed PostgreSQL custom-format dumps (`pg_dump -Fc`), creates SHA256 checksums, and prunes backups older than 7 days while always preserving the newest backup.
- **`restore-postgres.sh`**: Verifies and tests restoration into a temporary database (`mediscanai_restore_test`) by default; requires explicit `--force-production-restore` with interactive safety prompts for live restoration.
- **`maintenance.sh`**: Weekly host storage manager. Enforces exact repository ownership, locks named volumes and active/rollback images, rotates container logs, and respects storage utilization thresholds.
- **`production-status.sh`**: Comprehensive health and resource dashboard showing container states, APFS disk headroom, Docker resource usage, and recent deployment/backup history.

### 3.2 GitHub Actions Workflows (`.github/workflows/`)

- **`pr-ci.yml`**: Fast PR validation running on every PR targeting `main`:
  1. *Backend Fast CI*: Python syntax check, SQLite in-memory test suite (88 tests), maintenance safety tests (19 tests).
  2. *Frontend Lint & Build*: Oxlint code inspection and Vite production bundle compilation.
  3. *iOS Unit Tests*: Xcode build and native XCTest suite (62 tests) targeting iOS Simulator on `macos-15` runner.
- **`nightly-ci.yml`**: Nightly comprehensive regression suite running full end-to-end tests, UI tests, and dependency audits.
- **`docker-publish.yml`**: Triggers upon merge to `main`. Builds an optimized multi-stage ARM64 Docker image (`linux/arm64`) and pushes it to GHCR (`ghcr.io/djcode0718/mediscanai-backend:sha-<commit>`).
- **`deploy-production.yml`**: Environment-gated deployment workflow requiring manual approval. Connects to MacBook Air M4 via Tailscale mesh and executes `deployment/scripts/deploy.sh`.

### 3.3 macOS Scheduled Maintenance (`deployment/launchd/`)

- **`ai.mediscan.maintenance.plist`**: Validated LaunchAgent running weekly at 03:00 AM Sunday.
- **Installed Location:** `~/Library/LaunchAgents/ai.mediscan.maintenance.plist`.
- **Status:** Loaded and active via `launchctl`.

---

## 4. Test & Verification Summary

### 4.1 Verification Matrix

| Suite / Check | Environment | Test Count / Status | Execution Time | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Lint** (`oxlint`) | Local / CI | 0 errors, 11 style warnings | 0.08s | **PASS** |
| **Frontend Build** (`vite build`) | Local / CI | Clean production bundle | 0.17s | **PASS** |
| **Backend Unit Tests** | Local / CI | 88 passed (SQLite in-memory) | 20.54s | **PASS** |
| **Maintenance Safety Tests** | Local / CI | 19 policy tests passed | 9.86s | **PASS** |
| **iOS Unit Tests** | Local / macOS-15 | 62 passed (SwiftUI/Combine) | 0.08s | **PASS** |
| **Deploy Script Dry-Run** | MacBook Air M4 | Headroom & config valid | 0.42s | **PASS** |
| **Rollback Script Dry-Run**| MacBook Air M4 | History validation passed | 0.21s | **PASS** |
| **Production Status** | MacBook Air M4 | Full report generated | 0.65s | **PASS** |

### 4.2 Storage & Host Resource Audit

- **Host Machine:** Apple MacBook Air M4 (macOS Sequoia 15.x)
- **APFS Data Volume (`/System/Volumes/Data`):**
  - Total Size: 460 GiB
  - Available Headroom: **68 GiB free** ($>15\text{ GiB}$ required minimum)
  - Storage State: Healthy (Threshold $<70\%$)
- **Docker Desktop Allocation:**
  - CPUs: 10 cores
  - Memory: 7.75 GiB
  - Disk Limit: Configured within 32–48 GB boundary
  - Existing Images: 5 images (1.62 GB total)
  - Named Volumes: 18 volumes (1.85 GB total)
  - Build Cache: 0 B

---

## 5. Operations Governance & Next Steps

Phase 6.5 is formally complete. All automated CI checks, deployment scripting, and host safeguards have been implemented and verified.

The production server remains clean and protected. Remote production deployment will activate as soon as the user merges PR #2 and configures the required GitHub Secrets (`TAILSCALE_AUTHKEY`, `MACBOOK_SSH_KEY`, `MACBOOK_SSH_KNOWN_HOSTS`).
