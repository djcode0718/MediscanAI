# MediScanAI — Production CI/CD & Operations Runbook

**Target Platform:** MacBook Air M4 (Persistent Local Server & Development Workstation)  
**Architecture:** Apple Silicon ARM64 (`linux/arm64`)  
**Network Connectivity:** Private Tailscale Mesh Tunnel (`tag:ci-cd`)  
**Container Engine:** Docker Compose v2 (Multi-stage non-root containerization)  
**Budget & Cloud Infrastructure:** ₹0 / month (Zero paid cloud dependencies)

---

## 1. System Architecture Overview

```
Developer Workstation
        │ (git push)
        ▼
GitHub Pull Request (PR)
        │
        ├─► [Workflow: pr-ci.yml] (Fast Checks: ~3 min)
        │     ├─ Python Syntax & Bytecode Compilation
        │     ├─ Fast Backend Unit Tests (69 tests, SQLite in-memory, mocked boundaries)
        │     ├─ Frontend Lint & Production Asset Build (Vite)
        │     └─ Native iOS Debug Build & Unit Tests (62 tests, iPhone 16 Simulator)
        │
Merge into main branch
        │
        ▼
[Workflow: docker-publish.yml] (ARM64 Buildx: ~5 min)
        │
        ├─ Multi-stage build (Python 3.10 slim, CPU PyTorch)
        ├─ GitHub Actions layer cache (type=gha)
        └─ Push immutable image to GitHub Container Registry (GHCR)
             - Tag: ghcr.io/<owner>/mediscanai-backend:sha-<commit_sha>
             - Tag: ghcr.io/<owner>/mediscanai-backend:latest
        │
        ▼
[Workflow: deploy-production.yml] (Approval-Gated CD)
        │
        ├─ GitHub Environment: 'production' (Manual Approval Required)
        ├─ Concurrency Lock: 'production-deployment' (No concurrent mutations)
        ├─ Private Tailscale Mesh Authentication (tailscale/github-action@v3)
        ├─ Secure SSH Tunnel to MacBook Air M4 (Internal Tailscale IP / MagicDNS)
        │
        ▼ (On MacBook Air M4 Host)
deployment/scripts/deploy.sh
        ├─ 1. Check Docker daemon responsiveness
        ├─ 2. Evaluate SSD disk thresholds (<70% normal, 70-80% warning, >=90% block)
        ├─ 3. Validate deployment/.env (file permissions 600)
        ├─ 4. Record current image tag for rollback guarantee
        ├─ 5. Take pre-deployment PostgreSQL safety backup (backup-postgres.sh)
        ├─ 6. Pull exact immutable image from GHCR
        ├─ 7. Restart backend service (docker compose up -d --no-deps backend)
        │     └─ PRESERVES postgres_data, model_cache, and caddy_data volumes
        ├─ 8. Execute health-check.sh (/api/health and /api/ready)
        │
        ├─► SUCCESS: Update .current_deployment and log to .deployment_history
        └─► FAILURE: Trigger automated rollback.sh restoring previous known-good image
```

---

## 2. GitHub Actions Workflows

### A. Pull Request CI (`.github/workflows/pr-ci.yml`)
- **Triggers:** Pull requests targeting `main`, pushes to `feat/**` and `feature/**`.
- **Concurrency:** `cancel-in-progress: true` per PR branch.
- **Security:** Least-privilege `contents: read`.
- **Jobs:**
  1. `backend-checks` (Ubuntu 22.04):
     - Syntax and compilation check (`python -m compileall`).
     - Fast unit tests using in-memory SQLite (`sqlite:///:memory:`).
     - Covers authentication APIs, health probes, input sanitizers, rate limiters, Prompt V2 structures, security bounds, settings hygiene, and concurrency limiter.
     - Execution time: ~90 seconds.
  2. `frontend-checks` (Ubuntu 22.04):
     - Oxlint and Vite bundle compilation (`npm run lint`, `npm run build`).
     - Execution time: ~45 seconds.
  3. `ios-checks` (macOS 14 Apple Silicon runner):
     - Builds Debug simulator target and executes 62 focused native unit tests (`MediScanAITests`).
     - Execution time: ~2.5 minutes.

### B. Nightly Regression CI (`.github/workflows/nightly-ci.yml`)
- **Triggers:** Scheduled daily at 03:00 UTC (`cron: '0 3 * * *'`), manual `workflow_dispatch`.
- **Jobs:**
  1. `backend-full-integration`:
     - Isolated `postgres:15-alpine` service container.
     - Runs Alembic database migrations (`alembic upgrade head`).
     - Runs PostgreSQL database layer and API integration tests.
  2. `ios-full-suite`:
     - Executes both unit tests (`MediScanAITests`) and UI automation tests (`MediScanAIUITests`) against iOS Simulator.
  3. `frontend-regression`:
     - Verifies production bundle integrity.

### C. Docker Image Build & GHCR Publishing (`.github/workflows/docker-publish.yml`)
- **Triggers:** Merge/push to `main`, release tags (`v*.*.*`), or manual dispatch.
- **Registry:** GitHub Container Registry (`ghcr.io`).
- **Target Image:** `ghcr.io/<owner>/mediscanai-backend`.
- **Architecture:** `linux/arm64` (Apple Silicon M4 production target). Built on GitHub-hosted `ubuntu-22.04` runners using QEMU emulation (`docker/setup-qemu-action`) and Docker Buildx to cross-compile native `linux/arm64` container images.
- **Caching:** GitHub Actions Cache (`type=gha,mode=max`).
- **Tagging Strategy:**
  - `sha-${{ github.sha }}`: **Immutable reference** used for all CD deployments.
  - `latest`: Convenience pointer for `main`.
  - `vX.Y.Z`: Semantic release tags.

### D. Production Deployment CD (`.github/workflows/deploy-production.yml`)
- **Triggers:** Upstream completion of `docker-publish.yml` from `main`, or manual dispatch.
- **Environment Gate:** `production` environment with required reviewer sign-off.
- **Concurrency:** `group: production-deployment`, `cancel-in-progress: false`.
- **Network Tunnel:** Private Tailscale overlay network (zero open public ports).
- **Failure Recovery:** Automatically executes `deployment/scripts/rollback.sh` if the health check fails.

---

## 3. Required GitHub Secrets & Variables

Configure these settings under **GitHub Repository -> Settings -> Secrets and variables -> Actions**:

### Repository Secrets (`Settings -> Secrets and variables -> Actions -> Secrets`)

| Secret Name | Description | Example / Format |
| :--- | :--- | :--- |
| `TAILSCALE_AUTHKEY` | Tailscale pre-authenticated reusable or OAuth auth key tagged `tag:ci-cd` | `tskey-auth-k...` |
| `MACBOOK_SSH_KEY` | Ed25519 private SSH key for remote command execution on the Mac | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `MACBOOK_SSH_KNOWN_HOSTS` | **Mandatory** pinned SSH host key line (StrictHostKeyChecking=yes) | `<host> ssh-ed25519 AAAAC3...` |

*To securely obtain `MACBOOK_SSH_KNOWN_HOSTS` on the Mac host:*
```bash
# Extract the Mac host's ed25519 public host key and prefix with Tailscale IP/hostname:
echo "<MACBOOK_TAILSCALE_HOST> $(cat /etc/ssh/ssh_host_ed25519_key.pub)"
```

### Repository Variables (`Settings -> Secrets and variables -> Actions -> Variables`)

| Variable Name | Description | Example / Format |
| :--- | :--- | :--- |
| `MACBOOK_TAILSCALE_HOST` | Tailscale 100.x.y.z IP address or MagicDNS hostname of the MacBook Air M4 | `100.85.12.34` or `macbook-air.tailnet.ts.net` |
| `MACBOOK_DEPLOY_USER` | Local macOS user account on the MacBook Air | `sj` |

### GitHub Environment Configuration (`Settings -> Environments`)
1. Create an environment named `production`.
2. Enable **Required reviewers** and add your GitHub user account.
3. Set **Deployment branches** to `main` only.

---

## 4. Tailscale Private Mesh Setup Guide

To enable private, encrypted deployments from GitHub-hosted runners to your MacBook Air M4 without exposing SSH or port 8000 to the public internet:

### Step 1: Install Tailscale on the MacBook Air M4
```bash
# Using Homebrew Cask:
brew install --cask tailscale

# Or download directly from the Mac App Store.
```
Open Tailscale, sign in with your account, and connect.

### Step 2: Configure Access Control Lists (ACLs) in Tailscale Admin Console
In the [Tailscale Admin Console](https://login.tailscale.com/admin/acls), configure tags. Both `tag:ci-cd` and `tag:production-host` must be declared under `tagOwners`:
```json
{
  "tagOwners": {
    "tag:ci-cd": ["autogroup:admin"],
    "tag:production-host": ["autogroup:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:ci-cd"],
      "dst": ["tag:production-host:22"]
    }
  ]
}
```

### Step 3: Generate a Pre-authenticated Key for CI/CD
1. Navigate to **Tailscale Admin Console -> Settings -> Keys**.
2. Click **Generate auth key**.
3. Enable **Reusable** (or use OAuth client credentials).
4. Add tag: `tag:ci-cd`.
5. Copy the generated key and save it as `TAILSCALE_AUTHKEY` in GitHub Secrets.

### Step 4: Configure Remote Login (SSH) on the MacBook
1. Open **System Settings -> General -> Sharing**.
2. Turn on **Remote Login** (SSH), restricted to your account (`sj`).
3. Generate a dedicated deploy keypair:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-mediscanai-deploy" -f ~/.ssh/id_ed25519_deploy -N ""
   cat ~/.ssh/id_ed25519_deploy.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
4. Copy `~/.ssh/id_ed25519_deploy` (private key) into GitHub Secrets as `MACBOOK_SSH_KEY`.
5. Copy the host's public key into `MACBOOK_SSH_KNOWN_HOSTS`.
5. Verify that SSH is accessible over the Tailscale IP (`100.x.y.z`).

---

## 5. Production Operations Scripts (`deployment/scripts/`)

All operational scripts reside in `deployment/scripts/` and have executable permissions:

### 1. `deploy.sh`
Deploys an immutable image to production with preflight verification and storage safety.
```bash
# Production deployment:
./deployment/scripts/deploy.sh --image ghcr.io/<owner>/mediscanai-backend:sha-abc1234

# Dry-run simulation (verifies Docker, storage, and env without modifying containers):
./deployment/scripts/deploy.sh --image ghcr.io/<owner>/mediscanai-backend:sha-abc1234 --dry-run
```

### 2. `rollback.sh`
Restores the backend service to the previous known-good deployment without touching PostgreSQL.
```bash
# Automated rollback to last recorded known-good image:
./deployment/scripts/rollback.sh

# Explicit rollback to specific image tag:
./deployment/scripts/rollback.sh --image ghcr.io/<owner>/mediscanai-backend:sha-prev1234
```

### 3. `health-check.sh`
Probes backend liveness (`/api/health`) and readiness (`/api/ready`).
```bash
./deployment/scripts/health-check.sh --url http://localhost:8000 --timeout 10 --retries 5
```

### 4. `production-status.sh`
Displays the real-time operational status dashboard.
```bash
./deployment/scripts/production-status.sh
```
Output includes:
- Host SSD storage utilization with threshold warnings.
- Docker daemon state and container service statuses.
- API liveness and readiness probe responses.
- Active image tag and recent deployment history.
- PostgreSQL backup status and Docker disk utilization.

### 5. `backup-postgres.sh`
Creates compressed, timestamped logical PostgreSQL dumps and verifies archive integrity.
```bash
# Create backup with default 7-day retention:
./deployment/scripts/backup-postgres.sh

# Custom retention and directory:
./deployment/scripts/backup-postgres.sh --retention-days 14 --backup-dir /path/to/backups
```

### 6. `restore-postgres.sh`
Safely tests or executes database restoration.
```bash
# Safe verification mode: Restores into temporary test database (mediscanai_restore_test):
./deployment/scripts/restore-postgres.sh --file deployment/backups/mediscanai_postgres_20261119_120000.dump.gz --test-db

# Live production restoration (DESTRUCTIVE, requires interactive confirmation):
./deployment/scripts/restore-postgres.sh --file deployment/backups/mediscanai_postgres_20261119_120000.dump.gz --force-production-restore
```

### 7. `maintenance.sh`
Enforces storage hygiene without risking production data.
```bash
# Dry-run inspection (default):
./deployment/scripts/maintenance.sh --dry-run

# Execute cleanup:
./deployment/scripts/maintenance.sh --force
```

---

## 6. Storage Retention & Resource Safeguards

The MacBook Air M4 has a unified internal SSD (460 GiB APFS container) and acts as both development workstation and server. The operations system enforces the following explicit policies:

| Resource | Retention Policy | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Active Docker Image** | Kept indefinitely | Recorded in `deployment/.current_deployment` |
| **Rollback Images** | Last 2 known-good images preserved | Recorded in `deployment/.deployment_history` |
| **Dangling Images** | Removed during maintenance | `docker image prune -f` in `maintenance.sh` |
| **Obsolete Backend Images**| Removed if not in protected list | Targeted `mediscanai-backend` image prune in `maintenance.sh` |
| **Unrelated Docker Projects**| **Permanently Exempt** | Images/volumes of other projects (e.g. `paxel`, etc.) are never touched |
| **Build Cache** | Shared across host projects | Not pruned automatically; pruned only via `--prune-build-cache` |
| **Container Logs** | Max 30 MB per container (10MB x 3 files) | Configured in `deployment/compose.yaml` logging options |
| **PostgreSQL Data** | **Permanently Protected** | Named volume `mediscanai_postgres_data` is locked |
| **AI Model Cache** | **Permanently Protected** | Named volume `mediscanai_model_cache` is locked |
| **Database Backups** | 7 days retention (newest always preserved) | Automated verification and pruning in `backup-postgres.sh` |
| **Temporary Files** | Deleted after 24 hours | Strict allowlist `/private/tmp/mediscan_*` in `maintenance.sh` |

### Storage Threshold & Headroom Policy
Storage utilization on macOS is evaluated on `/System/Volumes/Data` (the APFS volume holding user and container data):
- `< 70%`: **Normal** — Headroom healthy.
- `70% – 79%`: **Notice** — Logged in deployment report.
- `80% – 89%`: **High Warning** — Maintenance cleanup recommended.
- `>= 90%`: **CRITICAL BLOCK** — `deploy.sh` halts immediately to prevent SSD exhaustion.
- **Minimum Absolute Headroom:** At least **15 GiB** of free space is required before any deployment can proceed (covers image pull, layer extraction, rollback retention, and pre-deployment database backup). If free space is below 15 GiB, deployment is blocked regardless of percentage.

### Docker Desktop Host Configuration Recommendations
- **Virtual Disk Limit:** In Docker Desktop (**Settings -> Resources -> Advanced**), set the virtual disk limit to **32 GB – 48 GB**. On macOS APFS, `Docker.raw` is a sparse file (currently allocating ~14 GB of physical SSD space). Setting an upper boundary guarantees Docker cannot consume unexpected disk space.
- **Resource Allocation:** Allocate **8 GB RAM** and **6–8 CPU cores** to Docker Desktop, leaving ample memory and CPU for macOS workstation tasks.

---

## 7. Automated Maintenance Scheduling (macOS `launchd`)

A validated LaunchAgent template is tracked in the repository at `deployment/launchd/ai.mediscan.maintenance.plist`.

To install and activate the weekly recurring maintenance job on the MacBook Air M4:

```bash
# 1. Copy the plist to user LaunchAgents:
cp deployment/launchd/ai.mediscan.maintenance.plist ~/Library/LaunchAgents/

# 2. Ensure log directory exists:
mkdir -p /Users/sj/Documents/mediscanai/deployment/logs

# 3. Load the launchd agent:
launchctl load ~/Library/LaunchAgents/ai.mediscan.maintenance.plist
```

Features:
- **Weekly Execution:** Runs every Sunday at 03:00 AM (or upon system wake).
- **Concurrency Locking:** Atomic lock (`/tmp/mediscanai_maintenance.lock.d`) prevents overlapping maintenance runs.
- **Bounded Logging:** Logs to `deployment/logs/maintenance.log` and automatically rotates logs exceeding 5 MB.
- **Dry-run vs Force:** `maintenance.sh` defaults to `--dry-run`; the LaunchAgent invokes `--force` to apply tested, safe maintenance actions.

---

## 8. Manual Activation Checklist

The CI/CD workflows and deployment scripts are fully implemented, tested, and committed locally. When you are ready to activate live remote deployments from GitHub Actions to your MacBook Air M4, complete these manual steps:

- [ ] **Step 1:** Push branch `feat/mediscanai-cicd-operations` to GitHub and open a Pull Request.
- [ ] **Step 2:** In GitHub repository settings, configure Environment `production` with required reviewers.
- [ ] **Step 3:** Add GitHub Secret `TAILSCALE_AUTHKEY` (tagged `tag:ci-cd`).
- [ ] **Step 4:** Add GitHub Secret `MACBOOK_SSH_KEY` (deploy key matching MacBook `~/.ssh/authorized_keys`).
- [ ] **Step 5:** Add GitHub Variable `MACBOOK_TAILSCALE_HOST` (MacBook Tailscale IP e.g. `100.x.y.z`).
- [ ] **Step 6:** Add GitHub Variable `MACBOOK_DEPLOY_USER` (MacBook username e.g. `sj`).
- [ ] **Step 7:** On MacBook Air, ensure Tailscale is connected and Remote Login (SSH) is enabled.
- [ ] **Step 8:** Merge PR into `main`. The `docker-publish.yml` workflow will build and publish the ARM64 image to GHCR, triggering `deploy-production.yml` for your review and approval!
