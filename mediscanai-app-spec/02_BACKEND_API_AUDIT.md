# MediScanAI — Backend API Inventory & Contract Specification

**Document:** `mediscanai-app-spec/02_BACKEND_API_AUDIT.md`  
**Status:** Verified Technical Specification  
**Backend Framework:** FastAPI 1.0.0 (Python 3.10/3.12, Uvicorn)  
**Contract Baseline:** `backend/main.py`, `backend/api/`, `backend/schemas/`, `backend/core/`  
**Compatibility Rule:** The existing API contracts must remain strictly backward-compatible. Zero breaking changes.

---

## 1. Overview & Protocol Architecture

The MediScanAI backend provides RESTful JSON and multipart APIs for identity management, health monitoring, multimodal clinical analyses, and historical records retrieval.

### Core Architectural Characteristics
1. **Host & Port:** Default local binding at `http://127.0.0.1:8000` (FastAPI/Uvicorn). In containerized mode, Caddy proxies `http://localhost:80` and `https://localhost:443`.
2. **CORS Headers:** Explicitly configured via `CORSMiddleware` in `backend/main.py`:
   - Allowed origins: `http://localhost:5173`, `http://127.0.0.1:5173`, `*`.
   - Exposed headers: `X-Request-ID`.
3. **Correlation ID:** Every request is assigned a unique UUID via `CorrelationIdMiddleware` (`backend/core/middleware.py`). If the client provides `X-Request-ID`, it is preserved; otherwise, a fresh UUID4 is generated and returned in response headers.
4. **Authentication:** Bearer token authentication in the HTTP header:
   ```http
   Authorization: Bearer <JWT_ACCESS_TOKEN>
   ```
   Tokens are signed with HMAC-SHA256 (`HS256`) and contain `sub: <user_id>` and `exp`. Expiration is 60 minutes.

---

## 2. Complete API Route Inventory

| Route | HTTP Method | Auth Required | Description / Purpose | Request Content-Type | Status Codes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | No | Root basic ping & environment info | None | `200` |
| `/api/health` | `GET` | No | Liveness probe (fast, lightweight) | None | `200` |
| `/api/ready` | `GET` | No | Readiness probe (checks DB, models, LLM) | None | `200`, `503` |
| `/api/auth/register` | `POST` | No | Account registration | `application/json` | `201`, `400` |
| `/api/auth/login` | `POST` | No | User login & JWT issuance | `application/json` | `200`, `400`, `401` |
| `/api/auth/me` | `GET` | Yes (Bearer) | Current user profile | None | `200`, `401` |
| `/api/analyze` | `POST` | Yes (Bearer) | Multimodal AI analysis execution | `multipart/form-data` | `200`, `400`, `401`, `429`, `500`, `503` |
| `/api/analyses` | `GET` | Yes (Bearer) | Paginated list of user's past analyses | Query parameters | `200`, `401` |
| `/api/analyses/{id}` | `GET` | Yes (Bearer) | Retrieve single detailed analysis record | Path parameter | `200`, `401`, `404` |
| `/api/analyses/{id}` | `DELETE` | Yes (Bearer) | Permanently delete analysis record | Path parameter | `200`, `401`, `404` |

---

## 3. Detailed Route Specifications

### 3.1 `GET /api/health` — Liveness Probe
- **Purpose:** Answers whether the FastAPI process is alive and responsive. Does not perform downstream database queries.
- **Headers:** None required.
- **Success Response (`200 OK`):**
  ```json
  {
    "status": "alive",
    "app": "MediScanAI",
    "environment": "development",
    "timestamp": 1731892800.123
  }
  ```

---

### 3.2 `GET /api/ready` — Readiness Probe
- **Purpose:** Determines if the instance is ready to accept heavy multimodal requests. Checks:
  1. PostgreSQL database connectivity (`check_db_connection()`).
  2. Machine learning models loaded (PaddleOCR pre-warmed, Faster-Whisper loaded, FAISS pipeline loaded).
  3. LLM service status: If `LLM_MODE == "online"`, returns `"not_required"`; if `"offline"`, verifies Ollama is reachable.
- **Success Response (`200 OK`):**
  ```json
  {
    "status": "ready",
    "app": "MediScanAI",
    "environment": "development",
    "components": {
      "database": "connected",
      "models_loaded": "ready",
      "ocr_prewarmed": "ready",
      "ollama_service": "not_required"
    },
    "concurrency": {
      "active_slots": 0,
      "max_concurrent": 2
    }
  }
  ```
- **Failure Response (`503 Service Unavailable`):**
  ```json
  {
    "detail": {
      "status": "not_ready",
      "components": {
        "database": "disconnected",
        "models_loaded": "not_loaded",
        "ocr_prewarmed": "failed_or_pending",
        "ollama_service": "unavailable"
      }
    }
  }
  ```

---

### 3.3 `POST /api/auth/register` — User Registration
- **Rate Limit:** 20 requests / minute per IP.
- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "Jane Doe"
  }
  ```
  *Validation Rules:*
  - `email`: Valid email format (via `pydantic[email]` / `EmailStr`).
  - `password`: Minimum 8 characters.
  - `full_name`: Optional string, max 255 characters.
- **Success Response (`201 Created`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "full_name": "Jane Doe",
      "is_active": true,
      "created_at": "2026-11-18T01:30:00Z"
    }
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Email already registered (`{"detail": "An account with this email address is already registered."}`).
  - `422 Unprocessable Entity`: Validation failure (short password, invalid email syntax).

---

### 3.4 `POST /api/auth/login` — User Authentication
- **Rate Limit:** 20 requests / minute per IP.
- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "full_name": "Jane Doe",
      "is_active": true,
      "created_at": "2026-11-18T01:30:00Z"
    }
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid credentials (`{"detail": "Invalid email or password"}`). Generic error prevents account enumeration.
  - `400 Bad Request`: Inactive account (`{"detail": "Inactive user account."}`).

---

### 3.5 `GET /api/auth/me` — Current User Profile
- **Request Headers:** `Authorization: Bearer <token>`
- **Success Response (`200 OK`):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "is_active": true,
    "created_at": "2026-11-18T01:30:00Z"
  }
  ```
- **Error Response (`401 Unauthorized`):** Invalid, missing, or expired token.

---

### 3.6 `POST /api/analyze` — Multimodal AI Analysis
- **Rate Limit:** 10 requests / minute per authenticated user ID.
- **Concurrency Guard:** Maximum 2 simultaneous analyses (`MAX_CONCURRENT_ANALYSES = 2`).
- **Request Headers:**
  - `Authorization: Bearer <token>` (Required)
  - `Content-Type: multipart/form-data`
- **Multipart Form Fields:**
  | Field Name | Type | Presence | Validation Constraints |
  | :--- | :--- | :--- | :--- |
  | `text` | Form String | Optional | Max 4,000 characters. User symptoms or medical questions. |
  | `image` | Binary File | Optional | Max 10 MB. Extensions: `.jpg`, `.jpeg`, `.png`, `.webp`. Verified magic bytes. |
  | `audio` | Binary File / List | Optional | Max 25 MB per file. Max 5 clips. Extensions: `.wav`, `.mp3`, `.webm`, `.ogg`, `.m4a`. Verified magic bytes. |
  *Constraint:* At least one of `text`, `image`, or `audio` must be provided.
- **Success Response (`200 OK`):**
  ```json
  {
    "analysis_id": 42,
    "card": {
      "user_text": "Dry cough and low fever in evenings",
      "ocr_text": "BEPLEX FORTE Multivitamin Tablets",
      "llm_output": "Based on the information provided, the medicine identified from the package, which appears to be **Beplex Forte**, is **not suitable** for treating your symptoms of a dry cough and fever.\n\nExplanation:\nBeplex Forte is a B-complex vitamin supplement intended to treat nutritional deficiencies...\n\n### Suggested Alternatives\n* **Dextromethorphan**: Oral cough suppressant...\n* **Paracetamol**: Antipyretic...\n\n### ⚠️ Important Warning\nThis analysis is for informational purposes only...",
      "retrieved": {
        "diseases": [
          {
            "key": "chunk_102",
            "score": 0.8245,
            "preview": {
              "disease": "Acute Bronchitis",
              "symptoms": ["dry cough", "fever", "fatigue"]
            }
          }
        ],
        "drugs": [
          {
            "key": "drug_512",
            "score": 0.7912,
            "preview": {
              "brand_name": "Dextromethorphan HBr",
              "generic_name": "Dextromethorphan",
              "indications_and_usage": "Temporary relief of coughs due to minor throat irritation"
            }
          }
        ],
        "drug_dict": [
          {
            "key": "dict_88",
            "score": 0.9521,
            "preview": {
              "brand_name": "Beplex Forte",
              "generic_name": "Vitamin B-Complex with Vitamin C"
            }
          }
        ]
      }
    },
    "meta": {
      "mismatch": null,
      "mismatch_details": "Mismatch check not performed in this pipeline version.",
      "ocr_status": "SUCCESS"
    },
    "timings": {
      "whisper_ms": 120,
      "ocr_total_ms": 340,
      "retrieval_diseases_ms": 15,
      "retrieval_drugs_ms": 18,
      "retrieval_drug_dict_ms": 12,
      "retrieval_drugs_from_ocr_ms": 14,
      "prompt_assembly_ms": 2,
      "llm_total_ms": 1250,
      "db_persistence_ms": 8,
      "total_duration_ms": 1980
    }
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Empty input, file size exceeded, invalid magic bytes, or file extension rejected.
  - `401 Unauthorized`: Session expired or invalid token.
  - `429 Too Many Requests`: Rate limit exceeded (`{"detail": "Rate limit exceeded. Please wait 12 seconds...", "Retry-After": "12"}`).
  - `503 Service Unavailable`: Max concurrent slots occupied (`{"detail": "MediScanAI is currently processing maximum concurrent clinical analyses...", "Retry-After": "5"}`).

---

### 3.7 `GET /api/analyses` — List Analysis History
- **Request Headers:** `Authorization: Bearer <token>`
- **Query Parameters:**
  - `limit`: Integer (default 20, min 1, max 100).
  - `offset`: Integer (default 0, min 0).
- **Success Response (`200 OK`):**
  ```json
  {
    "items": [
      {
        "id": 42,
        "modality": "multimodal",
        "status": "completed",
        "verdict": "Based on the information provided, the medicine identified from the package, which appears to be Beplex Forte, is not suitable for treating your symptoms of a dry cough and fever.",
        "processing_duration_ms": 1980,
        "created_at": "2026-11-18T01:35:00Z"
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  }
  ```

---

### 3.8 `GET /api/analyses/{id}` — Retrieve Analysis Detail
- **Request Headers:** `Authorization: Bearer <token>`
- **Path Parameter:** `id` (integer)
- **Ownership Rule:** Strict tenant isolation. If `analysis.user_id != current_user.id`, returns `404 Not Found`.
- **Success Response (`200 OK`):**
  ```json
  {
    "id": 42,
    "user_id": 1,
    "modality": "multimodal",
    "status": "completed",
    "verdict": "Based on the information provided...",
    "summary_card": {
      "user_text": "...",
      "ocr_text": "...",
      "llm_output": "...",
      "retrieved": { ... }
    },
    "processing_duration_ms": 1980,
    "created_at": "2026-11-18T01:35:00Z"
  }
  ```
- **Error Response (`404 Not Found`):** Record does not exist or belongs to another user.

---

### 3.9 `DELETE /api/analyses/{id}` — Delete Analysis
- **Request Headers:** `Authorization: Bearer <token>`
- **Path Parameter:** `id` (integer)
- **Success Response (`200 OK`):**
  ```json
  {
    "status": "deleted",
    "id": 42
  }
  ```
- **Error Response (`404 Not Found`):** Record not found or unowned.

---

## 4. Contract Guidance for Native iOS Client

1. **Exact Multipart Boundary & Part Names:**
   - Field `text`: plain UTF-8 string form field.
   - Field `image`: file part with filename (e.g. `image.jpg`) and content type (`image/jpeg`).
   - Field `audio`: file part with filename (e.g. `voice.m4a` or `voice.wav`). If multiple audio clips are submitted, repeat field name `audio` for each file.
2. **Handle `Retry-After` on HTTP 429 and 503:**
   - The iOS networking client should inspect the `Retry-After` response header and provide a calm countdown or auto-retry capability.
3. **Session Expiry Handling:**
   - On encountering HTTP 401 on any protected route, the app should clear the Keychain token and route the user cleanly back to the authentication screen.

