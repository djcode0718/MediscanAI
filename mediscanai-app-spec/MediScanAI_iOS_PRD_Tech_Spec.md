# MediScanAI iOS — Product Requirements & Technical Specification

**Document Version:** 1.0 (Audited & Reconciled Implementation Specification)  
**Status:** Approved for Native Implementation  
**Platform:** Native iOS 17.0+ (Swift 5.10 / 6.0, SwiftUI)  
**Initial Connectivity:** Same Local Wi-Fi as Host Mac Backend (`http://<LAN_IP>:8000`)  
**Backend Strategy:** 100% Reuse of existing FastAPI Backend, PostgreSQL DB, and AI Pipeline  
**Non-Negotiable Constraint:** Existing website functionality, API behavior, and database state must remain 100% undisturbed and operational.

---

## 1. Product Overview

MediScanAI iOS is a dedicated native iPhone client for the verified capabilities provided by the MediScanAI clinical intelligence project. It is **not** a webview wrapper, an alternative website, or an independent AI backend. The native app communicates with the existing FastAPI backend using standard HTTP/REST and streaming multipart payloads.

The first milestone is **Local-Network Execution**: the backend runs on the developer's MacBook Air M4 (via Docker Compose or native Python) and the iPhone communicates over the local Wi-Fi network. Future remote access via Tailscale is accommodated in the networking architecture with zero client-side refactoring required.

### 1.1 Core Objectives
- Deliver a quiet, minimalist, true-black OLED native iOS experience.
- Provide end-to-end access to the core MediScanAI workflows: packaging OCR, voice symptom logging, text analysis, and historical records.
- Seamlessly reuse the existing authentication engine, PostgreSQL database, and multimodal AI pipeline.
- Maintain a strict zero-regression guarantee for the existing web application.
- Maintain the project's **₹0/month** infrastructure guarantee by executing inference locally or through verified zero-cost online fallbacks.

### 1.2 Out of Scope
- Rewriting or duplicating the AI/ML pipeline in Swift or CoreML.
- Introducing paid third-party AI APIs or cloud infrastructure.
- Exposing the backend or database to the public internet via open router port-forwarding.
- Presenting AI outputs as an authoritative medical diagnosis or replacement for a licensed physician.

---

## 2. Verified User Personas & Core Journeys

### User Persona
An individual utilizing an iPhone to safely review medication packaging, transcribe verbal symptom logs, evaluate drug-symptom suitability, and access historical analyses.

### Verified User Journeys (Fully Mapped to Backend Routes)
1. **Account Registration & Sign-In:** Authenticate against `/api/auth/register` or `/api/auth/login`, persisting JWT credentials securely in Apple Keychain.
2. **Medicine Packaging Inspection:** Capture packaging photo using native camera or select from photo library; submit to `/api/analyze` for PaddleOCR extraction and suitability verification.
3. **Symptom Logging & Analysis:** Enter symptoms via text or voice recording; submit to `/api/analyze` for hybrid FAISS disease/drug matching and LLM evaluation.
4. **Multimodal Analysis:** Combine packaging photo, voice clip, and text notes into a single multipart submission.
5. **Results & Safety Review:** Review structured verdict (Danger / Success / Caution), clinical explanation, suggested alternatives, and collapsible RAG evidence.
6. **Historical Record Inspection & Deletion:** View chronological history list via `/api/analyses`, inspect past result cards, and permanently prune records via `DELETE /api/analyses/{id}`.
7. **Profile & Local Connection Setup:** Verify account details, configure Mac LAN IP address, and test connectivity via `/api/health`.

---

## 3. Information Architecture & Navigation

The native application adopts a clean, native 4-tab bar navigation model:

```
[ Tab 1: Home ]       --> Dashboard, quick scan CTA, recent analyses preview
[ Tab 2: Scan ]       --> Fullscreen camera viewfinder & photo preview sheet
[ Tab 3: History ]    --> Chronological paginated history list & detail viewer
[ Tab 4: Profile ]    --> Account info, Wi-Fi IP configuration, legal disclaimers, sign-out
```

*Note:* Symptom and Voice entry are accessible directly from high-visibility quick-action cards on the Home tab or from the unified composer.

---

## 4. Verified Backend API Contracts & Schemas

### 4.1 Endpoint Inventory
| Method | Path | Auth | Content-Type | Backend Handler |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | None | None | Liveness probe (`backend/main.py:184`) |
| `GET` | `/api/ready` | None | None | Readiness probe (`backend/main.py:198`) |
| `POST` | `/api/auth/register` | None | `application/json` | Registration (`backend/api/auth.py:21`) |
| `POST` | `/api/auth/login` | None | `application/json` | Login (`backend/api/auth.py:90`) |
| `GET` | `/api/auth/me` | Bearer | None | Profile rehydration (`backend/api/auth.py:160`) |
| `POST` | `/api/analyze` | Bearer | `multipart/form-data` | Multimodal analysis (`backend/main.py:250`) |
| `GET` | `/api/analyses` | Bearer | Query params | Paginated list (`backend/api/analyses.py:20`) |
| `GET` | `/api/analyses/{id}` | Bearer | None | Single record detail (`backend/api/analyses.py:61`) |
| `DELETE` | `/api/analyses/{id}` | Bearer | None | Record deletion (`backend/api/analyses.py:103`) |

### 4.2 Multipart Form Specification for `/api/analyze`
- **Field `text` (Form String):** Optional. Maximum 4,000 characters.
- **Field `image` (Binary File):** Optional. Maximum 10 MB. Allowed extensions: `.jpg`, `.jpeg`, `.png`, `.webp`. Validated binary magic bytes.
- **Field `audio` (Binary File / Repeated Parts):** Optional. Maximum 25 MB per file. Maximum 5 clips. Allowed extensions: `.wav`, `.mp3`, `.webm`, `.ogg`, `.m4a`. Validated binary magic bytes.
- **Header:** `Authorization: Bearer <TOKEN>` required.

### 4.3 Error Handling & Status Codes
- `400 Bad Request`: Validation failure (empty input, invalid file magic bytes, duplicate email).
- `401 Unauthorized`: Token expired or invalid. Clears Keychain and prompts sign-in.
- `404 Not Found`: Analysis record not found or owned by another user.
- `429 Too Many Requests`: Rate limit exceeded (10/min on `/api/analyze`). Client reads `Retry-After` header.
- `503 Service Unavailable`: Max concurrent slots occupied (2 concurrent limit). Client reads `Retry-After: 5` header.

---

## 5. Technical Architecture & Technology Stack

```
Native iOS App (Swift 5.10 / 6.0 · SwiftUI)
    │
    │ HTTP / REST + Streaming Multipart Form
    ▼
FastAPI Backend (MacBook Air M4)
    ├── JWT Authentication & Tenant Security
    ├── PaddleOCR Engine (Pre-warmed, thread-locked)
    ├── Faster-Whisper Speech STT (CPU int8)
    ├── Hybrid RAG (FAISS + BM25 + Cross-Encoder)
    ├── Emergency Triage Guardrails (112/911 Fast-Path)
    ├── Zero-Cost LLM Fallback (Gemini Flash -> Groq OSS)
    └── PostgreSQL 15 (Users, Data-Minimized Analyses, Audit Logs)
```

### iOS Technology Choices
- **SwiftUI:** Pure declarative UI with iOS 17 `@Observable` state management.
- **URLSession:** Small typed `APIClient` protocol with async/await. No third-party network libraries.
- **Keychain Services:** Secure Enclave token persistence (`kSecClassGenericPassword`).
- **AVFoundation:** Native `AVCaptureSession` for camera viewfinder and `AVAudioRecorder` for voice clips.
- **PhotosUI:** Native `PhotosPicker` for secure gallery selection.

---

## 6. Resolution of Discovery Questions

All discovery items identified during initial planning have been audited and resolved from the live codebase:

| Item | Verified Resolution from Repository |
| :--- | :--- |
| **Exact Website Feature Set** | User sign-in/up, symptom text entry, voice recording, image upload, multimodal execution, staged loading spinner, verdict styling, collapsible RAG evidence, history list/detail/delete, light/dark theme. |
| **Supported Auth Workflows** | Email + Password registration and login. Session token issued as JWT bearer (60 min expiration). Verified via `/api/auth/me`. Password reset and profile edit are currently unsupported on backend. |
| **Media Upload Constraints** | Image: max 10 MB (`.jpg`, `.jpeg`, `.png`, `.webp`). Audio: max 25 MB (`.wav`, `.mp3`, `.m4a`), max 5 clips. Text: max 4,000 characters. |
| **Structured Results Format** | Result contains `card` object with `llm_output`, `user_text`, `ocr_text`, and `retrieved` dictionaries (diseases, drugs, drug_dict). Verdict headline extracted from first markdown line. |
| **History Behavior** | Standard SQL pagination via `limit` (default 20, max 100) and `offset` (default 0). Strict user isolation enforced. Single item deletion via `DELETE /api/analyses/{id}`. |
| **Local Wi-Fi Host Binding** | Backend binds to `0.0.0.0:8000` or Caddy `0.0.0.0:80/443`. Reachable from iPhone on same Wi-Fi subnet. |
| **Minimum iOS Target** | iOS 17.0+ (enables modern SwiftUI `@Observable` and native `PhotosPicker`). |
| **Data Retention Policy** | Zero raw media retained on server or database. Files unlinked after inference. Database stores only structured text summary. |

---

## 7. Change-Control & Website Non-Regression Rule

1. **Additive Only:** All iOS-related files must live inside `ios/`.
2. **Zero Breaking Backend Changes:** Existing route signatures, response keys, database models, and environment settings must not be altered.
3. **Automated Verification:** Every code commit must pass the non-regression gate:
   - `cd frontend && npm run build` (exit 0).
   - `cd frontend && npm run lint` (0 errors).
   - `pytest tests/unit tests/api tests/database tests/test_e2e_smoke.py` (32/32 tests pass).
