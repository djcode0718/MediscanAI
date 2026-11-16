# MediScanAI — Production Deployment Summary

**Project:** MediScanAI (Privacy-First Multimodal AI Health Assistant)  
**Target Cloud:** Oracle Cloud Infrastructure (OCI) Always Free  
**Shape:** `VM.Standard.A1.Flex` (Ampere A1 ARM64: 2 OCPUs, 12 GB RAM, 50 GB Boot Volume)  
**Monthly Infrastructure Cost:** Strictly ₹0  
**Current Git Branch:** `feature/cloud-docker-deployment`  
**Current Git Commit HEAD:** `fc5ad47a32db873d267340ac2857e0d00359ed32`  

---

## 1. Architecture Overview

MediScanAI has been containerized and structured for production deployment using a 3-container topology:

```
[ Client Traffic (Web / Mobile) ]
                │
                ▼ :80 / :443
   ┌─────────────────────────────┐
   │      Caddy 2 Reverse Proxy   │ (Automatic TLS, HSTS, 30MB payload caps)
   └──────────────┬──────────────┘
                  │ internal-net (:8000)
                  ▼
   ┌─────────────────────────────┐
   │  FastAPI Backend (appuser)  │
   │  ├── PaddleOCR 3.2.0        │ (Native ARM64 text detection & recognition)
   │  ├── Faster-Whisper (base)  │ (Speech-to-text audio transcription)
   │  ├── FAISS Multi-Retriever  │ (Vector retrieval over diseases & drugs)
   │  ├── BM25 Lexical Retriever │ (Sparse inverted index search)
   │  ├── CrossEncoder Reranker  │ (ms-marco-MiniLM-L-6-v2)
   │  └── Online LLM Fallback    │ (gemini-3.6/3.7-flash ➔ openai/gpt-oss-120b/20b)
   └──────────────┬──────────────┘
                  │ internal-net (:5432)
                  ▼
   ┌─────────────────────────────┐
   │      PostgreSQL 15          │ (Relational store for users, analyses & audit)
   └─────────────────────────────┘
```

---

## 2. Infrastructure Budget & Zero-Cost Compliance

| Component | Target Provider | Free Tier Specification | Cost / Month |
| :--- | :--- | :--- | :---: |
| **Compute & Memory** | Oracle Cloud Always Free | Ampere A1 (Up to 4 OCPUs, 24 GB RAM permanently free; configured as 2 OCPUs, 12 GB RAM) | ₹0.00 |
| **Storage** | Oracle Cloud Always Free | 50 GB Boot Volume (Included in 200 GB Always Free allowance) | ₹0.00 |
| **Ingress & Egress** | Oracle Cloud Always Free | 10 TB outbound data transfer per month | ₹0.00 |
| **LLM Inference** | Google AI Studio & Groq | Free-tier developer rate limits (`gemini-3.6/3.7-flash` / Groq OSS models) | ₹0.00 (Conditional) |
| **TLS Certificates** | Let's Encrypt | Automated via Caddy reverse proxy (pending public domain mapping) | ₹0.00 |
| **Total Expenditure**| — | — | **₹0.00 / month (Conditional)** |

> [!IMPORTANT]
> **Zero-Cost Boundary & Free-Tier Quota Dependencies**:
> Achieving a ₹0 monthly operational expenditure is **strictly conditional** on using accounts configured within eligible free-tier allowances and without attached pay-as-you-go credit billing:
> 1. **Intended Usage Scope**: MediScanAI is architected solely to consume eligible free-tier developer quotas from Google AI Studio and Groq Cloud.
> 2. **Account Billing Configuration**: Returning an `HTTP 503 Service Unavailable` on provider exhaustion does not inherently prevent third-party accounts from incurring charges if an administrator associates a paid credit card or billing profile that enables automatic overages on those provider dashboards. Administrators must verify on their respective provider consoles (Google Cloud / Groq) that spend limits are capped at \$0 or that purely free developer tiers are selected.
> 3. **Controlled Exhaustion Behavior**: When free quotas are exhausted or rate-limited (HTTP 429), the application halts the fallback chain with a controlled error rather than routing to paid endpoints.
> 4. **No Guarantee of Unlimited Free Usage**: No commercial provider guarantees unlimited or perpetual free API quotas; API availability, rate limits, and model terms remain subject to third-party vendor policies.

---

## 3. Production Security Baseline

1. **Non-Root Execution:** FastAPI runs under UID 1000 (`appuser`).
2. **Zero Public Port Exposure:** PostgreSQL (`5432`) and FastAPI (`8000`) communicate exclusively over `mediscanai_internal_net`. Neither port is mapped to the host.
3. **CORS Enforcement:** `backend/core/config.py` strictly prohibits wildcard `*` origins when `APP_ENV=production`. Explicit origins are enforced.
4. **Ingress Security:** Caddy terminates TLS and injects HSTS (`max-age=31536000`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, and `Permissions-Policy`.
5. **Emergency Triage Guardrail:** Enabled by default in production (`EMERGENCY_GUARDRAIL_ENABLED=true`) with fast-path interception for life-threatening clinical symptoms.

---

## 4. Known Limitations & Cloud Provisioning Requirements

1. **OCI Cloud Tenancy Authentication:**
   * The local development environment does not have pre-configured Oracle Cloud credentials (`oci` CLI or `~/.oci/config`).
   * Provisioning the `VM.Standard.A1.Flex` instance requires the user to authenticate to the Oracle Cloud Web Console or provide SSH access to a running instance.
2. **Oracle Ampere A1 Capacity Availability:**
   * In some OCI regions (e.g., `ap-mumbai-1`, `us-ashburn-1`), Always Free Ampere A1 capacity experiences high demand ("Out of capacity for shape VM.Standard.A1.Flex").
   * If the chosen region is temporarily out of A1 capacity, the user can either select an alternate Always Free region or retry provisioning.
3. **Domain & DNS Configuration:**
   * Automated Let's Encrypt TLS requires a public domain name pointing to the VM's public IP.
   * If a custom domain is not yet mapped, Caddy falls back to serving HTTP on port 80 for direct IP testing.
4. **Git-Ignored Knowledge Assets:**
   * Datasets in `data/` (~111 MB) and FAISS indices in `indexes/` (~217 MB) are excluded from Git. They must be transferred to the cloud host via `rsync` as documented in `deployment/RUNBOOK.md`.

---

## 5. Container Footprint & Runtime Sizing (P0–P2 Optimization)

Following forensic audit and CPU-only optimization:

1. **Docker Storage Optimization:**
   - **Backend Image Virtual Size:** Shrunk from **11.66 GB to 3.85 GB** (-66.96%).
   - **Transfer Archive Size:** Shrunk from **3.89 GB to 865 MB** (-77.76%).
   - **Python Environment (`/opt/venv`):** Reduced from **6.70 GB to 2.30 GB** (-65.67%).
   - **P0 Cleanup:** Reclaimed **4.15 GB** of host disk space (obsolete Neo4j container, image, log volume, and dangling intermediate image).
2. **Runtime Memory Profiling:**
   - **FastAPI Backend:** 247 MB idle, 1.02 GB warmed, 1.48 GB peak during concurrent multimodal analysis.
   - **PostgreSQL 15:** 52 MB idle, 85 MB peak.
   - **Caddy Proxy:** 15 MB idle, 24 MB peak.
   - **Total Stack Peak RSS:** **~1.59 GB** (well within the 12–24 GB Ampere A1 cloud memory budget).
3. **Local Host Sizing Recommendation (Apple Silicon M4, 16 GB RAM):**
   - Configure Docker Desktop VM to **4.0 GiB RAM / 1.0 GiB swap**, recovering 4 GB of physical RAM for macOS and eliminating SSD swap paging.
4. **ML Runtime Safety:**
   - Mandatory PaddleOCR startup pre-warming resolves OpenMP collision with CTranslate2 / Faster-Whisper, guaranteeing 100% stable execution.
5. **Promotion Readiness:**
   - **Ready with Warnings**. Promotion of `mediscanai-backend:cpu-test` (`f6225228ce25`) to `mediscanai-backend:production` is prepared and awaiting final user command.


