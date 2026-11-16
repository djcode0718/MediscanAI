# MediScanAI — Architectural Blueprint: Current vs. Cloud Deployment

**Document Version:** 1.0.0 (Phase 1 Baseline)  
**Target Infrastructure:** Oracle Cloud Always Free (Ampere A1: 2 OCPUs, 12 GB RAM)  
**Cost Target:** Strictly ₹0 / month  

---

## 1. Architectural Evolution Overview

MediScanAI is an evidence-grounded multimodal AI health assistant that reads medicine packaging labels, transcribes spoken patient symptom narratives, performs hybrid dense+sparse knowledge retrieval with cross-encoder reranking, and synthesizes clinical guidance via online LLM APIs.

```mermaid
flowchart TD
    subgraph Clients["Supported Client Applications"]
        WEB["React 19 + Vite Web Application<br/>(Desktop & Mobile Browsers)"]
        IOS["Future Native iOS Application<br/>(SwiftUI on iPhone 16 Pro Max)"]
    end

    subgraph CloudBoundary["Oracle Cloud Always Free VM (Linux aarch64 - 2 OCPU / 12 GB RAM)"]
        subgraph Ingress["Ingress & Edge Security"]
            CADDY["Caddy Reverse Proxy<br/>(Port 80/443, Automated TLS, Rate Limiting)"]
        end

        subgraph Containers["Docker Production Network (Internal Bridge)"]
            FASTAPI["MediScanAI Backend Container<br/>FastAPI + Uvicorn + Pipeline Runtime<br/>(Port 8000 Internal)"]
            POSTGRES["PostgreSQL 15 Container<br/>Users, Analyses, Audit Events<br/>(Port 5432 Internal)"]
        end

        subgraph PersistentStorage["Host Persistent Block Storage (/opt/mediscanai)"]
            PGDATA[("PostgreSQL Data Volume<br/>pgdata")]
            DATA_VOL[("Read-Only Datasets<br/>/data/*.jsonl")]
            IDX_VOL[("Read-Only Vector Indexes<br/>/indexes/*.index")]
            CACHE_VOL[("Model Cache Volume<br/>HuggingFace & Paddle weights")]
        end
    end

    subgraph ExternalServices["External Zero-Cost Online AI Services"]
        GEMINI["Google Gemini Models<br/>(gemini-3.6-flash / gemini-3.7-flash)"]
        GROQ["Groq Fast OSS Models<br/>(openai/gpt-oss-120b / openai/gpt-oss-20b)"]
    end

    WEB -->|HTTPS / WSS| CADDY
    IOS -->|HTTPS REST API| CADDY
    CADDY -->|Reverse Proxy :8000| FASTAPI
    FASTAPI -->|Internal SQLAlchemy Pool| POSTGRES
    FASTAPI -->|Read-Only Index Access| IDX_VOL
    FASTAPI -->|Read-Only Dataset Access| DATA_VOL
    FASTAPI -->|Model Weights| CACHE_VOL
    POSTGRES -->|Persistent Reads/Writes| PGDATA
    FASTAPI -->|HTTPS TLS Rest API| GEMINI
    FASTAPI -->|HTTPS TLS Rest API| GROQ
```

---

## 2. Current Local Implementation vs. Proposed Cloud Architecture

| Component | Current Local Development State | Proposed Production Cloud State | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Host System** | macOS Darwin ARM64 (Apple Silicon M4) | Ubuntu 24.04 LTS aarch64 (Oracle Cloud Ampere A1) | Maximizes Always Free compute (2 OCPU / 12 GB RAM at ₹0/mo). |
| **Web Ingress** | Direct Uvicorn exposure (`127.0.0.1:8000`) | Caddy 2 Reverse Proxy (`:80` / `:443`) | Automated Let's Encrypt TLS certificates, security headers, request throttling. |
| **Database Exposure**| Exposed on `0.0.0.0:5432` in Docker Compose | Bound strictly to internal Docker bridge network | Closes critical security hole; prevents public database port exposure. |
| **LLM Inference** | Local Ollama (`llama3.1:8b` via Metal/CPU) | Pure Online APIs (`gemini-3.6/3.7-flash` + Groq `gpt-oss-120b/20b`) | Eliminates 6–8 GB local Ollama RAM load; offloads generation to external online LLMs (measured complete pipeline request: 31.98s; total pipeline execution duration in database: 31,930 ms). |
| **Readiness Probe** | Unconditionally checks Ollama at `/api/ready` | Dynamic check based on `LLM_MODE` | Prevents container restarts when running in pure cloud online mode. |
| **OCR Engine** | PaddleOCR (PaddlePaddle 3.0 lazy singleton) | PaddleOCR (PaddlePaddle 3.0 Linux aarch64) | Preserves PaddleOCR text extraction pipeline; verified via unit tests (`test_ocr.py`) on synthetic medicine strips with native ARM64 wheels. |
| **Embeddings & Vector**| Local SentenceTransformers + FAISS-CPU | Local SentenceTransformers + FAISS-CPU | Zero external API latency for vector search; pre-computed indexes mounted read-only. |
| **Knowledge Graph** | Neo4j 5.26 container declared in Compose | Excluded from minimal production Compose stack | Neo4j is optional (`NEO4J_ENABLED=false`). Saves 2.5 GB JVM memory on 12 GB VM. |
| **Model Caching** | Local `~/.cache` directory on host | Dedicated persistent Docker named volume | Eliminates repeated 450 MB model weight downloads on container recreation. |
| **Image Size** | Single-stage development build | Multi-stage Dockerfile | Measured local image: 11.66 GB uncompressed (3.89 GB containerd content size). Excludes build tools (`gcc`, `g++`, make); uses `opencv-python-headless`. |

---

## 3. Detailed Request Lifecycle & Internal Data Flow

The following sequence diagram traces an end-to-end multimodal analysis request through the application stack:

```mermaid
sequenceDiagram
    autonumber
    actor User as Patient / Client (React / iOS)
    participant Caddy as Caddy Proxy (TLS)
    participant API as FastAPI Router (/api/analyze)
    participant Auth as JWT Auth & Audit Layer
    participant Whisper as Faster-Whisper (CPU int8)
    participant OCR as PaddleOCR Engine
    participant Guard as Emergency Guardrail
    participant Retr as MultiRetriever (FAISS + BM25)
    participant Cross as CrossEncoder (ms-marco)
    participant LLM as Online LLM (Gemini / Groq)
    participant DB as PostgreSQL 15

    User->>Caddy: POST /api/analyze (multipart: text, image, audio)
    Caddy->>API: Proxy validated request with X-Request-ID
    API->>Auth: Validate Bearer JWT token & rate limit (user:id)
    Auth-->>API: Active User identity confirmed

    opt Voice Audio Provided
        API->>Whisper: Transcribe audio clips in worker thread (asyncio.to_thread)
        Whisper-->>API: Extracted symptom narrative text
    end

    opt Medicine Image Provided
        API->>OCR: Extract label text & bounding boxes (PaddleOCR)
        OCR-->>API: Extracted medication strings
    end

    API->>Guard: Emergency fast-path triage evaluation
    alt Critical Life-Threatening Emergency Detected
        Guard-->>API: Immediate emergency referral text
    else Normal Analysis Path
        par Symptom Channel Retrieval
            API->>Retr: search_specific("diseases", symptoms)
            Retr-->>API: Ranked disease candidate chunks
            API->>Retr: search_specific("drugs", symptoms)
            Retr-->>API: Ranked indication candidate chunks
        and Medication Channel Retrieval
            API->>Retr: search_specific("drug_dict", ocr_text)
            Retr-->>API: Matched generic entities
            API->>Retr: search_specific("drugs", ocr_text)
            Retr-->>API: Matched drug monographs
        end

        API->>Cross: Rerank top candidates with query-document cross-attention
        Cross-->>API: Final top-k reranked evidence items

        API->>LLM: Dispatch structured clinical prompt (Gemini primary -> Groq fallback)
        LLM-->>API: Grounded clinical analysis & verdict markdown
    end

    API->>DB: Persist Analysis record (summary_card, timings, modality)
    API->>DB: Record operational audit event (ANALYSIS_CREATED)
    API-->>Caddy: JSON response {card, meta, timings, analysis_id}
    Caddy-->>User: HTTPS 200 OK Response
```

---

## 4. Component Lifecycle & Initialization State

```text
Application Startup (@app.on_event("startup")):
  ├── 1. PostgreSQL Connection Test (check_db_connection)
  ├── 2. Pre-warm RAG Pipeline (Pipeline.__init__)
  │     ├── Load FAISS indexes into memory (diseases, drugs, drug_dict) [~220 MB]
  │     ├── Build in-memory BM25 term frequency dictionaries [~280 MB]
  │     ├── Load SentenceTransformer embedding model ('all-MiniLM-L6-v2') [~150 MB]
  │     └── Load CrossEncoder reranker ('cross-encoder/ms-marco-MiniLM-L-6-v2') [~150 MB]
  ├── 3. Pre-warm Faster-Whisper Model ('base', compute_type="int8") [~180 MB]
  └── 4. Initialize Emergency Triage Guardrail (rule regex index) [~5 MB]

On-Demand (Lazy Initialization on First Request):
  └── PaddleOCR Model (PaddlePaddle 3.0 inference engine) [~650 MB]
        └── Triggered only when a user uploads a medicine image.
```

---

## 5. Storage & Volume Mount Mapping

```text
/opt/mediscanai/ (Host Root on Oracle Cloud VM)
  ├── .env.prod                                -> Read-only environment variables
  ├── docker-compose.prod.yml                  -> Production orchestration manifest
  ├── Caddyfile                                -> Reverse proxy routing configuration
  │
  ├── data/                                    -> Mounted to /app/data:ro inside container
  │     ├── diseases_faiss_data.jsonl (3.7 MB)
  │     ├── drug_dict_faiss_data.jsonl (2.9 MB)
  │     └── drugs_faiss_data.jsonl (103.4 MB)
  │
  ├── indexes/                                 -> Mounted to /app/indexes:ro inside container
  │     ├── diseases_faiss.index (5.2 MB)
  │     ├── drug_dict_faiss.index (89.6 MB)
  │     └── drugs_faiss.index (122.1 MB)
  │
  └── volumes/
        ├── pgdata/                            -> Named volume for PostgreSQL database
        ├── caddy_data/                        -> Automated TLS certificates & keys
        ├── caddy_config/                      -> Caddy internal configuration
        └── model_cache/                       -> Mounted to /home/appuser/.cache
              ├── huggingface/ (MiniLM, Whisper, CrossEncoder)
              └── paddlex/ (PaddleOCR weights)
```

