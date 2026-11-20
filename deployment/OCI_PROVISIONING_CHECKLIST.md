# MediScanAI — Oracle Cloud (OCI) Always Free Provisioning Checklist

**Target Infrastructure:** Oracle Cloud Infrastructure (OCI) Always Free — Ampere A1 ARM64
**Shape:** `VM.Standard.A1.Flex` (2 OCPUs, 12 GB RAM, 50 GB Boot Volume)
**Operating System:** Ubuntu 24.04 LTS Minimal (`aarch64`)
**Budget Constraint:** Strictly ₹0 / month
**Deployment Model:** 3-Container Topology (Caddy 2 + FastAPI CPU + PostgreSQL 15)

---

## Pre-Flight Classification Legend
- `[ ]` **Action Item**: Requires operator execution.
- `[x]` **Verified Item**: Validated during pre-provisioning engineering audit.
- `[!]` **Critical Safety Guard**: Requires strict adherence to prevent lockout or unexpected costs.

---

## 1. Prerequisites & Local Mac Preparation

- [x] **Local Image Built & Validated**: Production ARM64 image `mediscanai-backend:production` (`4ea6bb3f3e42`) is verified locally.
- [x] **Rollback Baseline Preserved**: Original baseline image preserved under `mediscanai-backend:rollback-baseline` (`1d080e38142b`).
- [x] **Management Scripts Prepared**: `preflight-check.sh`, `backup.sh`, and `restore.sh` are authored and executable.
- [ ] **Generate / Verify SSH Keypair on Mac**:
  ```bash
  # Check for existing key or generate a dedicated deployment key:
  ls -la ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -C "mediscanai-oci"
  ```
- [ ] **Export Compressed Production Image on Mac**:
  ```bash
  cd /Users/sj/Documents/mediscanai
  docker save mediscanai-backend:production | gzip > mediscanai-backend-production-arm64.tar.gz
  ls -lh mediscanai-backend-production-arm64.tar.gz
  # Expected size: ~865 MB (865,042,668 bytes)
  ```
- [ ] **Obtain Administrator Public IP (for SSH firewall restriction)**:
  ```bash
  ADMIN_IP=$(curl -s https://ifconfig.me)
  echo "Administrator Public IP: $ADMIN_IP"
  ```

---

## 2. Oracle Cloud Web Console Actions

Log in to the [Oracle Cloud Infrastructure Console](https://cloud.oracle.com).

### A. Virtual Cloud Network (VCN) & Security List Setup
- [ ] Navigate to **Networking > Virtual Cloud Networks**.
- [ ] Create a VCN using the **Start VCN Wizard > Create VCN with Internet Connectivity**:
  - **VCN Name:** `mediscanai-vcn`
  - **Compartment:** Root (or designated project compartment)
  - **VCN CIDR:** `10.0.0.0/16`
  - **Public Subnet CIDR:** `10.0.0.0/24`
- [ ] Navigate to **Security Lists > Default Security List for mediscanai-vcn**.
- [ ] Configure **Ingress Rules**:
  - [!] **Rule 1 (SSH - Port 22):**
    - Source CIDR: `<ADMIN_IP>/32` *(Restrict strictly to your public IP from Section 1)*
    - IP Protocol: `TCP`
    - Destination Port Range: `22`
    - Description: `SSH Administrative Access`
  - [ ] **Rule 2 (HTTP - Port 80):**
    - Source CIDR: `0.0.0.0/0`
    - IP Protocol: `TCP`
    - Destination Port Range: `80`
    - Description: `Caddy HTTP / ACME Challenge`
  - [ ] **Rule 3 (HTTPS - Port 443):**
    - Source CIDR: `0.0.0.0/0`
    - IP Protocol: `TCP`
    - Destination Port Range: `443`
    - Description: `Caddy Public HTTPS Ingress`
- [ ] Configure **Egress Rules**:
  - [ ] Verify default egress rule allows all outbound traffic (`0.0.0.0/0`) for package updates and LLM APIs.

### B. Compute Instance Creation (Ampere A1)
- [ ] Navigate to **Compute > Instances > Create Instance**.
- [ ] **Instance Name:** `mediscanai-prod-vm`
- [ ] **Placement:** Availability Domain (choose AD with available capacity; e.g., AD-1, AD-2, or AD-3).
- [ ] **Image and Shape:**
  - Click **Change Image** > Select **Canonical Ubuntu > Ubuntu 24.04 Minimal (aarch64)**.
  - Click **Change Shape** > Select **Ampere (ARM) > VM.Standard.A1.Flex**:
    - **OCPUs:** `2`
    - **Memory (GB):** `12`
    - *(Always Free eligible banner should appear)*.
- [ ] **Networking:**
  - Select `mediscanai-vcn` and the public subnet `10.0.0.0/24`.
  - **Public IPv4 address:** Select **Assign a public IPv4 address**.
- [ ] **Add SSH Keys:**
  - Select **Paste public keys** and paste the contents of `~/.ssh/id_rsa.pub`.
- [ ] **Boot Volume:**
  - Check **Specify a custom boot volume size**.
  - Set size to **50 GB** (well within the 200 GB Always Free allowance).
- [ ] Click **Create**.
- [ ] Wait for instance state to transition from *Provisioning* to *Running*. Record the assigned **Public IP Address**: `<OCI_VM_PUBLIC_IP>`.

---

## 3. Cloud Host Hardening & Environment Bootstrap

From your local Mac terminal:

- [ ] **Initial SSH Connection**:
  ```bash
  ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP>
  ```
- [ ] **System Updates & Base Utilities**:
  ```bash
  sudo apt update && sudo apt upgrade -y
  sudo apt install -y ca-certificates curl gnupg lsb-release ufw fail2ban rsync
  ```
- [ ] **Configure Host Firewall (UFW)**:
  ```bash
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow from <ADMIN_IP>/32 to any port 22 proto tcp comment "SSH admin access"
  sudo ufw allow 80/tcp comment "Caddy HTTP"
  sudo ufw allow 443/tcp comment "Caddy HTTPS"

  # CRITICAL: Keep current SSH session open. Enable UFW:
  sudo ufw --force enable
  sudo ufw status verbose
  ```
- [!] **Test SSH Connectivity in a Second Terminal Before Closing**:
  ```bash
  # In a NEW local terminal:
  ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP> "echo 'Firewall SSH verified'"
  ```
- [ ] **Configure Fail2ban for SSH**:
  ```bash
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
- [ ] **Install Official Docker Engine (ARM64)**:
  ```bash
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Allow non-root docker execution and activate group membership:
  sudo usermod -aG docker ubuntu
  newgrp docker
  docker --version && docker compose version
  ```
- [ ] **Create Directory Hierarchy**:
  ```bash
  mkdir -p ~/mediscanai/deployment ~/mediscanai/data ~/mediscanai/indexes ~/mediscanai/backups
  ```

---

## 4. Asset, Manifest & Image Transfer

From your local Mac terminal (`/Users/sj/Documents/mediscanai`):

- [ ] **Transfer Static Datasets & FAISS Indexes**:
  ```bash
  rsync -avz -e "ssh -i ~/.ssh/id_rsa" data/ ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/data/
  rsync -avz -e "ssh -i ~/.ssh/id_rsa" indexes/ ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/indexes/
  ```
- [ ] **Transfer Deployment Manifests & Management Scripts**:
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
  ```
- [ ] **Transfer and Load Compressed Docker Image**:
  ```bash
  # Upload image archive (865 MB)
  scp -i ~/.ssh/id_rsa mediscanai-backend-production-arm64.tar.gz ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/

  # On Cloud VM: Load image and remove archive to conserve 50 GB boot volume:
  ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP> "gunzip -c ~/mediscanai/mediscanai-backend-production-arm64.tar.gz | docker load && rm ~/mediscanai/mediscanai-backend-production-arm64.tar.gz"
  ```
- [ ] **Verify Loaded Image on Cloud VM**:
  ```bash
  ssh -i ~/.ssh/id_rsa ubuntu@<OCI_VM_PUBLIC_IP> "docker images"
  # Confirm mediscanai-backend:production is present with virtual size ~3.86 GB
  ```

---

## 5. Configuration, Preflight & Stack Deployment

On the Cloud VM:

- [ ] **Create Production `.env` File**:
  ```bash
  cd ~/mediscanai/deployment
  cp .env.example .env
  chmod 600 .env
  chmod +x *.sh
  nano .env
  ```
  *Configure strong values:*
  - `POSTGRES_PASSWORD`: Generate 32+ character random alphanumeric string.
  - `JWT_SECRET_KEY`: Generate via `openssl rand -hex 32`.
  - `GEMINI_API_KEY`: Add valid Google AI Studio developer API key.
  - `GROQ_API_KEY`: Add valid Groq Cloud developer API key.
  - `DOMAIN_NAME`: Set `:80` for initial IP testing, or `api.yourdomain.com` for public domain.
  - `CORS_ORIGINS`: Set `["http://<OCI_VM_PUBLIC_IP>"]` for IP test or `["https://app.yourdomain.com"]` for prod.

- [ ] **Execute Automated Preflight Verification**:
  ```bash
  ./preflight-check.sh
  ```
  *Verify that all 15 checks output `[PASS]` and script exits with code 0.*

- [ ] **Launch the Production Stack**:
  ```bash
  docker compose -f compose.yaml up -d
  ```

- [ ] **Verify Service Health Status**:
  ```bash
  docker compose -f compose.yaml ps
  ```
  *Expected:*
  - `mediscanai-postgres`: `Up (healthy)`
  - `mediscanai-backend`: `Up (healthy)`
  - `mediscanai-caddy`: `Up`

---

## 6. Smoke Testing & Verification

- [ ] **Verify Health & Readiness Endpoints**:
  ```bash
  curl -s http://localhost/api/health | jq .
  # Expected: {"status":"alive"}

  curl -s http://localhost/api/ready | jq .
  # Expected: {"status":"ready", "database":"connected", "models_loaded":"ready", "ocr_prewarmed":"ready", "ollama_service":"not_required"}
  ```
- [ ] **Verify User Registration & Login**:
  ```bash
  curl -s -X POST http://localhost/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"AdminPassword123!","full_name":"Admin User"}' | jq .

  TOKEN=$(curl -s -X POST http://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"AdminPassword123!"}' | jq -r .access_token)

  curl -s http://localhost/api/auth/me \
    -H "Authorization: Bearer $TOKEN" | jq .
  ```
- [ ] **Verify Memory Consumption Under Load**:
  ```bash
  docker stats --no-stream
  # Verify backend is <3.0 GB and total stack is <3.5 GB
  ```
- [ ] **Test Automated Backup & Safe Restore**:
  ```bash
  ./backup.sh
  DUMP_FILE=$(ls -t ~/mediscanai/backups/*/mediscanai_postgres_*.dump | head -n 1)
  ./restore.sh "$DUMP_FILE" --test-db
  # Confirm row counts are reported and test database drops cleanly
  ```

---

## 7. Public Domain & Automated SSL Finalization (Optional)

Once a public domain name is mapped via DNS A-Record to `<OCI_VM_PUBLIC_IP>`:

- [ ] **Update `deployment/.env`**:
  ```bash
  DOMAIN_NAME=api.yourdomain.com
  CORS_ORIGINS=["https://app.yourdomain.com", "https://yourdomain.com"]
  ```
- [ ] **Reload Caddy**:
  ```bash
  docker compose -f compose.yaml restart caddy
  ```
- [ ] **Verify Automated Let's Encrypt TLS**:
  ```bash
  curl -Iv https://api.yourdomain.com/api/health
  # Verify HTTP/2 200 OK and valid Let's Encrypt certificate
  ```

---

## 8. Scheduled Automated Maintenance & Disaster Recovery

- [ ] **Configure Daily Automated Backup Cron Job on Cloud VM**:
  ```bash
  crontab -e
  # Add entry to run daily at 03:00 UTC with 14-day retention:
  0 3 * * * /home/ubuntu/mediscanai/deployment/backup.sh /home/ubuntu/mediscanai/backups 14 >> /home/ubuntu/mediscanai/backups/backup.log 2>&1
  ```

- [ ] **Configure Off-Host Disaster Recovery Backup (from Local Mac)**:
  *To protect against total VM loss or cloud tenancy issues without incurring third-party cloud storage fees or billing risks, pull backups off-host to your local Mac:*
  ```bash
  # On local Mac: Pull backups to local directory periodically
  mkdir -p ~/mediscanai_cloud_backups
  rsync -avz -e "ssh -i ~/.ssh/id_rsa" ubuntu@<OCI_VM_PUBLIC_IP>:~/mediscanai/backups/ ~/mediscanai_cloud_backups/
  ```
  > [!IMPORTANT]
  > **Disaster Recovery Qualifications & Limitations**:
  > 1. Local Mac rsync pulls protect against VM loss **only after a transfer successfully completes**.
  > 2. A sleeping, powered-off, or offline Mac **cannot run scheduled synchronization**. Continuous disaster recovery cannot be guaranteed by client-side pulls alone.
  > 3. **Scheduling:** Recommend configuring a macOS `launchd` LaunchAgent (`~/Library/LaunchAgents/com.mediscanai.backupsync.plist`) with failure logging (`StandardErrorPath`), as `launchd` automatically runs missed jobs upon system wake.
  > 4. **Periodic Verification:** Periodically execute `./restore.sh <dump> --test-db` on the local machine against a local Docker container to verify the integrity of transferred backups.
  > 5. **Zero-Cost Constraint:** Do not configure third-party cloud storage (e.g. AWS S3, GCP GCS) to avoid unbudgeted recurring expenses.
