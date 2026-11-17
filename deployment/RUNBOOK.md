# MediScanAI — Operational Production Runbook

**Target Platform:** Oracle Cloud Infrastructure (OCI) Always Free — Ampere A1 ARM64 (`VM.Standard.A1.Flex`)  
**Operating System:** Ubuntu 24.04 LTS (aarch64)  
**Infrastructure Budget:** Strictly ₹0 / month  
**Stack Architecture:** Caddy 2 (Reverse Proxy / TLS) + FastAPI Multimodal Backend + PostgreSQL 15  

---

## 1. Initial Host Provisioning (Oracle Cloud Always Free)

> [!WARNING]
> **OCI Always Free Ampere A1 Capacity Notice**:
> Due to high demand, `VM.Standard.A1.Flex` capacity may occasionally be constrained in certain availability domains or regions ("Out of host capacity"). If provisioning fails with a capacity error:
> 1. Try selecting an alternative Availability Domain (AD-1, AD-2, AD-3) within your tenancy region.
> 2. Attempt provisioning during off-peak hours (e.g., early morning).
> 3. Consider an automated provisioning retry script (using OCI CLI) if manual creation is temporarily starved.
> Instance availability cannot be guaranteed at every instant in every region under Always Free.

> [!IMPORTANT]
> **Zero-Cost Policy & Free-Tier Quota Boundary**:
> This deployment is designed strictly for ₹0 / month, **conditional upon eligible free-tier quotas and account billing configuration**:
> 1. The Oracle Cloud Ampere A1 compute instance (2 OCPUs, 12 GB RAM) and 50 GB boot volume fall within Oracle's Always Free allowance.
> 2. Online LLM inference relies exclusively on eligible free-tier developer quotas from Google Gemini API and Groq Cloud.
> 3. **Billing Safeguards**: Returning an `HTTP 503` when providers are exhausted stops application retries, but does not configure external provider account billing. Administrators must verify on their respective provider consoles (Google Cloud / Groq) that spend limits are capped at $0 and that no paid auto-billing profile is active.
> 4. No paid fallback should be enabled without explicit authorization.
> 5. No commercial provider guarantees unlimited or perpetual free API quotas; if free quotas are exhausted, the application returns a controlled `HTTP 503 Service Unavailable` response.

### A. Instance Specifications
* **Shape:** `VM.Standard.A1.Flex` (Ampere A1 ARM64)
* **Compute Allocation:** 2 OCPUs, 12 GB RAM, 50 GB Boot Volume (well within the Always Free 4 OCPU / 24 GB / 200 GB tenancy limit)
* **Operating System:** Ubuntu 24.04 LTS Minimal (`aarch64`)
* **Network / VCN:**
  * Public Subnet with Internet Gateway
  * Security List Ingress Rules:
    * Port 22 (SSH) — **Required**: Restrict to administrator CIDR (`YOUR_PUBLIC_IP/32`) rather than `0.0.0.0/0` at the VCN Security List level to prevent brute-force attacks.
    * Port 80 (HTTP / ACME Challenge) — `0.0.0.0/0` (Required for Caddy automated Let's Encrypt certificate issuance)
    * Port 443 (HTTPS) — `0.0.0.0/0` (Public client access)
  * Security List Egress Rules:
    * All traffic (`0.0.0.0/0`) allowed outbound for online LLM APIs (Gemini/Groq), Ubuntu package mirrors, and HuggingFace asset downloads.

### B. OS Hardening, Firewall & Service Installation
Connect to the instance via SSH:
```bash
ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP>
```

Update system packages and install prerequisites, UFW, and Fail2ban:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release ufw fail2ban

# Configure host firewall (UFW)
# IMPORTANT: Restrict SSH to your administrator public IP to prevent unauthorized access.
# Replace YOUR_PUBLIC_IP with your actual public IPv4 address (find via: curl -s https://ifconfig.me).
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH strictly from administrator public IP:
sudo ufw allow from YOUR_PUBLIC_IP/32 to any port 22 proto tcp comment "SSH admin access"

# Allow public web traffic for Caddy reverse proxy:
sudo ufw allow 80/tcp comment "Caddy HTTP / ACME"
sudo ufw allow 443/tcp comment "Caddy HTTPS"

# SAFETY PROCEDURE TO PREVENT LOCKOUT:
# 1. Do NOT close your current SSH terminal session.
# 2. Enable UFW:
sudo ufw --force enable
sudo ufw status verbose

# 3. VERIFY BEFORE CLOSING: Open a SECOND terminal window on your local machine and verify SSH access:
#    ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP>
# 4. Only if the second session connects cleanly should you proceed.
#    If the second connection fails or hangs, run 'sudo ufw disable' in your first session to recover.

# Configure Fail2ban SSH jail
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo tee /etc/fail2ban/jail.d/sshd.local > /dev/null << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 1h
findtime = 10m
EOF

sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

Install Docker Engine for Linux `aarch64` (official Docker APT repository):
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Grant non-root user access to Docker
sudo usermod -aG docker ubuntu
newgrp docker
docker --version && docker compose version
```

### C. Create Deployment Directory Structure
```bash
mkdir -p ~/mediscanai/deployment ~/mediscanai/data ~/mediscanai/indexes ~/mediscanai/backups
cd ~/mediscanai
```

---

## 2. Asset & Image Transfer

### A. Transfer Static Knowledge Assets & Precomputed FAISS Indices
From the local development machine:
```bash
# Verify local file presence
ls -la data/ indexes/

# Transfer data/ (~111 MB) and indexes/ (~217 MB) to cloud host
rsync -avz -e "ssh -i ~/.ssh/id_rsa" data/ ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/data/
rsync -avz -e "ssh -i ~/.ssh/id_rsa" indexes/ ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/indexes/
```

### B. Transfer Deployment Manifests & Management Scripts
```bash
rsync -avz -e "ssh -i ~/.ssh/id_rsa" \
  deployment/compose.yaml \
  deployment/Caddyfile \
  deployment/Dockerfile \
  deployment/requirements.txt \
  deployment/docker-entrypoint.sh \
  deployment/preflight-check.sh \
  deployment/backup.sh \
  deployment/restore.sh \
  deployment/.env.example \
  ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/deployment/

# Ensure scripts have execution permissions on the VM
ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP> "chmod +x ~/mediscanai/deployment/*.sh"
```

### C. Transfer Verified ARM64 Docker Image
To maintain exact bitwise reproducibility without compiling dependencies on the cloud host (verified local image: `3.86 GB` uncompressed; compressed transfer archive: `~865 MB` / `865,042,668 bytes`):
```bash
# On local machine (save verified production image)
docker save mediscanai-backend:production | gzip > mediscanai-backend-production-arm64.tar.gz

# Transfer compressed image (~865 MB)
scp -i ~/.ssh/id_rsa mediscanai-backend-production-arm64.tar.gz ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/

# On cloud VM (load verified image)
gunzip -c ~/mediscanai/mediscanai-backend-production-arm64.tar.gz | docker load
docker images

# Clean up compressed archive to conserve host disk space on the 50 GB volume:
rm ~/mediscanai/mediscanai-backend-production-arm64.tar.gz
```

---

## 3. Production Configuration (`.env`)

On the cloud VM, create `~/mediscanai/deployment/.env`:
```bash
cp ~/mediscanai/deployment/.env.example ~/mediscanai/deployment/.env
chmod 600 ~/mediscanai/deployment/.env
nano ~/mediscanai/deployment/.env
```

Ensure the following variables are set:
```dotenv
APP_NAME=MediScanAI
APP_ENV=production
DEBUG=false

# Domain & HTTPS Configuration
# If a custom domain is configured, set: DOMAIN_NAME=api.yourdomain.com
# For initial IP testing or direct HTTP access, set: DOMAIN_NAME=:80
DOMAIN_NAME=:80

# Database Credentials (generate random string)
POSTGRES_USER=mediscanai
POSTGRES_PASSWORD=<STRONG_RANDOM_PASSWORD_32_CHARS>
POSTGRES_DB=mediscanai

# JWT Secret Key (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=<STRONG_RANDOM_SECRET_KEY_64_CHARS>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM Mode (strictly online for ₹0 cloud infrastructure)
LLM_MODE=online
ONLINE_LLM_TIMEOUT_SECONDS=60.0

# Online LLM Provider Keys
GEMINI_API_KEY=<YOUR_GEMINI_API_KEY>
GROQ_API_KEY=<YOUR_GROQ_API_KEY>

GEMINI_MODEL_1=gemini-3.6-flash
GEMINI_MODEL_2=gemini-3.7-flash
GROQ_MODEL_1=openai/gpt-oss-120b
GROQ_MODEL_2=openai/gpt-oss-20b

# CORS Configuration (Wildcards strictly prohibited in production)
# PRODUCTION REQUIREMENT: In production, include ONLY the exact HTTPS origins hosting your frontend.
# 'http://localhost:5173' is for local dev only and must NOT be in public production.
# For initial direct IP HTTP testing: CORS_ORIGINS=["http://<OCI_VM_PUBLIC_IP>"]
# For production HTTPS deployment:
CORS_ORIGINS=["https://app.yourdomain.com", "https://yourdomain.com"]

# Clinical Safety Guardrail
EMERGENCY_GUARDRAIL_ENABLED=true
EMERGENCY_GUARDRAIL_FAST_PATH=true
EMERGENCY_GUARDRAIL_CONFIG_PATH=app/guardrail_config.json
```

### Run Preflight Configuration Verification
Before starting the stack, validate environment configuration and secrets using the preflight check script:
```bash
cd ~/mediscanai/deployment
./preflight-check.sh
```
Expected output:
```text
============================================================
 MediScanAI — Production Deployment Preflight Check
============================================================
[PASS] .env file exists: /home/ubuntu/mediscanai/deployment/.env
[PASS] .env permissions are 600 (-rw-------)
[PASS] APP_ENV is set to 'production'
[PASS] DEBUG is set to 'false'
[PASS] POSTGRES_USER is set
[PASS] POSTGRES_PASSWORD is valid (strong)
[PASS] POSTGRES_DB is set: mediscanai
[PASS] JWT_SECRET_KEY is valid (strong, length: 64)
[PASS] LLM_MODE is set to 'online'
[PASS] GEMINI_API_KEY is configured
[PASS] GROQ_API_KEY is configured
[PASS] Local data directory exists: /home/ubuntu/mediscanai/data
[PASS] Local indexes directory exists: /home/ubuntu/mediscanai/indexes
[PASS] Docker daemon is running
[PASS] Docker Compose v2 is available
============================================================
PREFLIGHT CHECK SUMMARY: ALL CHECKS PASSED
Stack is ready for deployment.
============================================================
```

---

## 4. Stack Launch & Lifecycle Management

### A. Starting the Stack
```bash
cd ~/mediscanai/deployment
docker compose -f compose.yaml up -d
```

### B. Checking Service Status & Health
```bash
docker compose -f compose.yaml ps
```
Expected output:
* `mediscanai-postgres`: `Up (healthy)`
* `mediscanai-backend`: `Up (healthy)`
* `mediscanai-caddy`: `Up`

### C. Viewing Live Application Logs
```bash
# Follow all container logs
docker compose -f compose.yaml logs -f

# View backend logs only
docker logs -f --tail=100 mediscanai-backend

# View database logs only
docker logs -f --tail=100 mediscanai-postgres

# View Caddy access & reverse proxy logs
docker logs -f --tail=100 mediscanai-caddy
```

### D. Safe Restart Procedures
```bash
# Restart application backend without touching database
docker compose -f compose.yaml restart backend

# Restart reverse proxy
docker compose -f compose.yaml restart caddy

# Gracefully stop the entire stack (preserves persistent volumes)
docker compose -f compose.yaml down

# NEVER run 'docker compose down -v' in production, as -v deletes persistent database volumes!
```

---

## 5. Automated Backup & Restore Procedures

### A. Automated Production Backup (`backup.sh`)
Execute the standardized backup script to back up the PostgreSQL database, `.env` file, and Caddy TLS certificates:
```bash
cd ~/mediscanai/deployment
./backup.sh
```
This generates a timestamped directory under `~/mediscanai/backups/mediscanai_backup_<TIMESTAMP>/` containing:
- `mediscanai_postgres_<TIMESTAMP>.dump` (Custom format pg_dump)
- `env.backup` (chmod 600)
- `caddy_data/` (TLS certificates & account keys)

Optional arguments:
```bash
# Custom backup destination
./backup.sh /mnt/secure-backups

# Retain backups for 14 days (prunes backups older than N days)
./backup.sh ~/mediscanai/backups 14
```

### B. Safe Restore & Integrity Verification (`restore.sh`)
To verify backup data integrity safely without modifying the live database, run `restore.sh` in `--test-db` mode:
```bash
cd ~/mediscanai/deployment
./restore.sh ~/mediscanai/backups/mediscanai_backup_<TIMESTAMP>/mediscanai_postgres_<TIMESTAMP>.dump --test-db
```
This automatically:
1. Provisions an isolated temporary database (`mediscanai_restore_test`).
2. Restores the dump into the temporary database.
3. Queries and logs row counts for `users`, `analyses`, and `audit_logs`.
4. Automatically drops the temporary test database, ensuring zero modifications to the live production database.

### C. Emergency Production Database Restore
In a disaster recovery scenario where the live production database must be replaced:
```bash
cd ~/mediscanai/deployment
./restore.sh ~/mediscanai/backups/mediscanai_backup_<TIMESTAMP>/mediscanai_postgres_<TIMESTAMP>.dump --force-production-restore
```
*(Requires explicit typing of `RESTORE-PRODUCTION` to prevent accidental execution).*

---

### D. Manual Backup & Restore Procedures (Reference)
If managing backups directly via Docker CLI:
```bash
BACKUP_DIR=~/mediscanai/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Execute pg_dump inside the container
docker exec mediscanai-postgres pg_dump -U mediscanai -d mediscanai --format=custom -f /tmp/backup.dump
docker cp mediscanai-postgres:/tmp/backup.dump "$BACKUP_DIR/mediscanai_db_${TIMESTAMP}.dump"
docker exec mediscanai-postgres rm /tmp/backup.dump

# Enforce strict permissions
chmod 600 "$BACKUP_DIR/mediscanai_db_${TIMESTAMP}.dump"
echo "Backup created at: $BACKUP_DIR/mediscanai_db_${TIMESTAMP}.dump"
```

### E. Off-Host Disaster Recovery & Scheduling Limitations

> [!WARNING]
> **Host-Level Disaster Recovery Boundary & Limitations**:
> 1. **Local vs Off-Host Protection:** Backups stored in `~/mediscanai/backups/` protect against software defects, migration failures, and administrative errors on the VM, but **do not protect against termination, disk failure, or loss of the cloud VM itself**.
> 2. **Conditional Off-Host Protection:** Off-host replication to a local administrative machine (e.g., MacBook Air) protects against VM destruction **only after a successful transfer has completed**.
> 3. **Mac Sleep / Disconnect Limitations:** A local Mac that is asleep, shut down, or disconnected from the network **cannot run its scheduled synchronization job**. Therefore, continuous disaster recovery cannot be guaranteed by a client-side pull alone.
> 4. **Scheduling Recommendation:** Use macOS `launchd` (via a LaunchAgent) rather than standard cron, as `launchd` will automatically run missed jobs when the Mac wakes up and reconnects to the network. Configure dedicated error and standard logging.
> 5. **Periodic Restore Verification:** Off-host backups must be validated periodically by executing the safe test restore (`./restore.sh <dump> --test-db`) against a local test container.
> 6. **Zero-Cost & No Third-Party Storage:** Consistent with the ₹0 infrastructure budget, do not configure paid third-party cloud storage (AWS S3, GCP Cloud Storage) or automated paid storage tiers.

#### Recommended macOS `launchd` Job Setup (Local Mac)
Create `~/Library/LaunchAgents/com.mediscanai.backupsync.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mediscanai.backupsync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/rsync</string>
        <string>-avz</string>
        <string>-e</string>
        <string>ssh -i /Users/sj/.ssh/id_rsa</string>
        <string>ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/backups/</string>
        <string>/Users/sj/mediscanai_cloud_backups/</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/sj/mediscanai_cloud_backups/sync.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/sj/mediscanai_cloud_backups/sync_err.log</string>
</dict>
</plist>
```
Load the agent on macOS:
```bash
mkdir -p ~/mediscanai_cloud_backups
launchctl load ~/Library/LaunchAgents/com.mediscanai.backupsync.plist
```

---

## 6. System Monitoring & Resource Health

Run the following diagnostics to verify system health:

```bash
# Check memory, CPU, and network utilization across all containers
docker stats --no-stream

# Check host memory & swap usage
free -h

# Check disk space on host boot volume
df -h /

# Verify zero public port exposure on PostgreSQL
docker port mediscanai-postgres || echo "PostgreSQL has NO public ports (PASS)"
```

---

## 7. Emergency Recovery & Troubleshooting

### Scenario 1: Backend Reports Unhealthy (`503 Service Unavailable`)
1. Inspect backend logs:
   ```bash
   docker logs --tail=100 mediscanai-backend
   ```
2. Verify PostgreSQL connectivity:
   ```bash
   docker exec -it mediscanai-postgres pg_isready -U mediscanai -d mediscanai
   ```
3. Check memory limits:
   ```bash
   docker stats --no-stream mediscanai-backend
   ```

### Scenario 2: VM System Reboot Recovery
The production `compose.yaml` specifies `restart: unless-stopped` for all services:
1. When the Oracle Cloud VM reboots, Docker automatically restarts `mediscanai-postgres`, `mediscanai-backend`, and `mediscanai-caddy`.
2. The backend entrypoint automatically pings PostgreSQL, verifies schema migrations, and resumes serving requests.
3. Test reboot resilience by executing:
   ```bash
   sudo reboot
   ```
4. Reconnect after 60 seconds and confirm all containers are healthy:
   ```bash
   docker compose -f ~/mediscanai/deployment/compose.yaml ps
   ```

---

## 8. Health-Data Privacy & Data-Minimization Guidelines

MediScanAI handles multimodal health workflows: medicine packaging text extraction via PaddleOCR, user-reported clinical symptom narratives, drug interaction lookups via local FAISS/BM25 retrieval, and synthesis via online LLMs.

### Core Data-Minimization Principles:
1. **No Direct Personal Identifiers Required**:
   - MediScanAI does not solicit or require full legal names, government identity numbers, phone numbers, or residential addresses.
   - User registration requires only a functional email and password for authentication and audit log correlation.
   - Users and clinicians should be advised to avoid including patient names, birthdates, or contact details in symptom text narratives or uploaded image notes.

2. **Isolation of Account Identifiers from LLM Prompts**:
   - Prompts constructed for external LLM synthesis (`app/llm_providers.py`) must contain only clinical and pharmacological context (extracted OCR text, symptom description, retrieved drug monograph snippets, and safety guardrails).
   - User account IDs, emails, IP addresses, and database primary keys must never be concatenated into prompt payloads sent to third-party model providers.

3. **Log Sanitization & Minimization**:
   - Container logs (`docker logs mediscanai-backend`) and reverse proxy logs (`mediscanai-caddy`) must not emit raw medicine strip images, audio byte arrays, or full narrative inputs into unencrypted console stdout.
   - Ensure `DEBUG=false` in production `.env` to prevent verbose stack traces from leaking request bodies or authorization headers.

4. **Credential & Secret Protection**:
   - External provider API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) and database credentials must exist solely in the server's `deployment/.env` file with restrictive permissions (`chmod 600`).
   - Keys must never be exposed to client-side code (React frontend or future iOS client) or committed to version control.

5. **External LLM Provider Boundary**:
   - While in-transit transport security is enforced via HTTPS/TLS (Caddy) and database data is confined to an internal Docker network, requests routed to external LLM providers (Google Gemini, Groq Cloud) are subject to the terms of service, data processing agreements, and retention policies of those respective vendors.
   - MediScanAI provides application-level data minimization, but does not guarantee cryptographic external anonymity once prompts traverse the boundary to third-party commercial APIs. Administrators should consult provider-specific settings (e.g., zero-data-retention or enterprise tier settings) if deploying for clinical patient use.

