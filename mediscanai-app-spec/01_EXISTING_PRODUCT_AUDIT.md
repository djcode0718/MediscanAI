# MediScanAI — Existing Product & Web Application Audit

**Document:** `mediscanai-app-spec/01_EXISTING_PRODUCT_AUDIT.md`  
**Status:** Complete Technical Audit  
**Auditor:** Antigravity AI Engineering  
**Scope:** Frontend Architecture, Supported User Journeys, Feature Inventory, Operational Limitations, and UI State Machinery  
**Repository Working Tree:** Verified Clean (`main` branch @ `776390e`)

---

## 1. Executive Summary

MediScanAI is an active, local-first multimodal health intelligence application designed to assist users in understanding medical prescriptions, packaging labels, and clinical symptoms. The current product is delivered through a modern Single Page Application (SPA) built with **React 19.2.8** and **Vite 8.2.2**, communicating over REST with a **FastAPI 1.0.0** backend.

The application’s core proposition is **100% local privacy and zero-cost inference**: sensitive health inputs, captured packaging images, and voice recordings are processed on the host machine using localized models (PaddleOCR, Faster-Whisper, and local FAISS vector databases) with optional zero-cost online LLM fallback (Google Gemini Flash and Groq open-source models).

This audit documents the exact capabilities, components, and limitations of the existing web application to ensure that the forthcoming native iOS client delivers feature parity without altering or degrading the existing web client.

---

## 2. Frontend Architecture & Technology Stack

The web client lives in the `frontend/` directory and is structured as a decoupled SPA:

| Dimension | Implementation Details | Verified Source File |
| :--- | :--- | :--- |
| **Framework** | React 19.2.8 (`react`, `react-dom`) | `frontend/package.json` |
| **Build Tooling** | Vite 8.2.2 (`@vitejs/plugin-react` 6.0.4) | `frontend/vite.config.js` |
| **Styling** | Tailwind CSS 4.3.3 (`@tailwindcss/vite`) | `frontend/src/index.css` |
| **Icons** | Lucide React 1.33.0 (`lucide-react`) | `frontend/src/components/` |
| **Markdown Rendering** | React Markdown 10.1.0 + Remark GFM 4.0.1 | `frontend/src/components/Dashboard.jsx` |
| **Linter** | Oxlint 1.75.0 (`oxlint`) | `frontend/package.json` |
| **Production Bundle** | CSS: `49.76 kB` (8.68 kB gzip), JS: `397.44 kB` (120.14 kB gzip) | `frontend/dist/` build output |

### Component Hierarchy
```
frontend/src/App.jsx (Root Session Coordinator & Theme Controller)
├── LandingAuth.jsx (Unauthenticated View: Brand Hero, Value Cards, Sign In / Sign Up Forms)
└── Dashboard.jsx (Authenticated View: Two-Column Clinical Copilot)
    ├── Header Bar (Brand, Privacy Pill, User Profile Capsule, History Trigger, Theme Toggle, Sign Out)
    ├── Input Section (Left 5/12 column)
    │   ├── Symptoms Textarea (Input field, max 4000 chars)
    │   ├── Voice Recording & File Upload Controls (MediaRecorder API / audio file picker)
    │   ├── Audio Clip List (Inline playback, duration preview, clip deletion)
    │   ├── Medicine Label Photo Dropzone (Drag-and-drop / file browser, image preview, replace/remove)
    │   └── Submit Action Trigger ("Run Analysis" button with animated spinner)
    ├── Results Display Section (Right 7/12 column)
    │   ├── Idle Empty State ("Awaiting Local Query" with step-by-step explainer)
    │   ├── Loading State (Dual-ring spinner + 6-step progress message cycler + progress bar)
    │   └── Active Result View
    │       ├── Verdict Capsule (Danger / Success / Warning style with icon and headline)
    │       ├── Clinical Explanation (Markdown-rendered clinical rationale)
    │       ├── Suggested Alternatives (Markdown-rendered pharmacological alternatives)
    │       ├── Grounded Supporting Evidence (Collapsible accordions for Diseases, Drugs, Drug Dict)
    │       └── Mandatory Safety Warning (Contextual medical disclaimers)
    └── History Slide-Over Drawer
        ├── Paginated / Listed Analyses (Modality badge, timestamp, verdict snippet)
        ├── Inspect Detail Trigger (Loads historical analysis card into view)
        └── Delete Record Trigger (Permanent cascade deletion from PostgreSQL)
```

---

## 3. Supported User Journeys & Feature Matrix

### Journey 1: Authentication & Session Lifecycle
1. **User Sign Up (`POST /api/auth/register`):**
   - User inputs `full_name`, `email`, and `password`.
   - Client sends JSON payload `{ email, password, full_name }`.
   - On HTTP 201, client stores JWT `access_token` and user object in `localStorage` under `mediscan_auth_token` and `mediscan_auth_user`.
2. **User Sign In (`POST /api/auth/login`):**
   - User inputs `email` and `password`.
   - Client sends JSON payload `{ email, password }`.
   - On HTTP 200, JWT token and user profile are saved to `localStorage`.
3. **Session Rehydration & Validation (`GET /api/auth/me`):**
   - On application mount, `App.jsx` reads `mediscan_auth_token`.
   - If present, issues a bearer-authenticated request to `GET /api/auth/me`.
   - If HTTP 200: refreshes user state.
   - If HTTP 401: calls `clearAuth()`, wiping `localStorage` and redirecting to `LandingAuth`.
4. **Sign Out:**
   - Clears `localStorage`, resets React state, and returns immediately to the unauthenticated view.

### Journey 2: Symptom-Based Analysis (Text-Only)
- User enters natural language symptoms (e.g., *"Persistent dry cough with fever in evenings"*).
- User clicks **"Run Analysis"**.
- Client constructs `multipart/form-data` with field `text`.
- Dispatches `POST /api/analyze` with `Authorization: Bearer <token>`.
- Displays staged progress indicator while awaiting backend response.
- Renders structured verdict, explanation, and matched disease/drug contexts.

### Journey 3: Medicine Packaging Inspection (Vision / OCR)
- User drags and drops or browses a packaging photo (PNG, JPG, JPEG, WEBP; up to 10 MB).
- Client generates an instant in-memory object URL (`URL.createObjectURL`) for preview.
- User clicks **"Run Analysis"**.
- Client sends `image` as a binary file field in the multipart request.
- Backend runs **PaddleOCR**, extracts packaging text, and cross-references `drug_dict` and `drugs` FAISS indexes.
- Output presents identified medicine name, validity, and suitability.

### Journey 4: Multimodal Analysis (Symptoms + Image + Voice)
- User combines all three modalities simultaneously:
  1. Enters symptom text in textarea.
  2. Records voice audio clip via browser microphone (using `MediaRecorder`, WAV/WebM) or uploads audio file (MP3, WAV, M4A up to 25 MB).
  3. Uploads packaging photo.
- Form data bundles `text`, `image`, and multiple `audio` binary parts.
- Backend sequentially transcribes audio clips using **Faster-Whisper**, executes PaddleOCR, runs hybrid vector retrieval across all channels, and feeds the merged prompt to the LLM.

### Journey 5: Analysis History Review & Pruning
- User clicks **"History"** in the top navigation bar.
- Client requests `GET /api/analyses?limit=30` with Bearer auth.
- Slide-over drawer lists past records with:
  - Modality badge (`multimodal`, `text`, `image`, `audio`).
  - Creation timestamp.
  - Verdict headline snippet.
- Clicking an item requests `GET /api/analyses/{id}` and renders the complete historical card.
- Clicking the trash icon issues `DELETE /api/analyses/{id}`, immediately removing the card and updating the list.

### Journey 6: Appearance & Theme Preference
- Floating theme toggle switches between Light and Dark modes.
- Preference is persisted in `localStorage.theme` and synchronized with OS-level `prefers-color-scheme` listeners.
- Document root toggles the `.dark` class, adjusting Tailwind CSS styling dynamically.

---

## 4. Current Implementation Quality & Verification

A read-only baseline audit of the frontend was conducted using the project's build and lint tools:

1. **Production Build:**
   - Command: `cd frontend && npm run build`
   - Result: **SUCCESS** (Built 2,055 modules in 180ms with 0 compilation errors).
2. **Static Analysis & Linting:**
   - Command: `cd frontend && npm run lint` (Oxlint 1.75.0)
   - Result: **0 errors, 11 warnings**.
   - Verified that the warnings are purely benign (unused `HelpCircle` icon import, unused parameter variables in markdown component overrides, and synchronous setState in audio timer effect).

---

## 5. Identified Operational Limitations & Scope Boundaries

The existing web application exhibits several specific architectural characteristics that the native iOS app must respect:

1. **No Password Reset Flow:**
   - The backend does not expose `/api/auth/reset-password` or email verification endpoints.
   - The iOS client must not build an orphaned "Forgot Password" UI that lacks backend support.
2. **No User Profile Editing or Account Deletion:**
   - There are currently no endpoints for updating user name/email or self-service account deletion.
   - The iOS profile screen must display read-only user attributes and a clean sign-out action.
3. **No Refresh Token Rotation:**
   - JWT tokens are issued with a fixed expiration (default 60 minutes) without a `/api/auth/refresh` route.
   - When a token expires, the backend returns HTTP 401. Both web and iOS clients must catch 401 responses and gracefully prompt re-authentication.
4. **Local Concurrency Throttle:**
   - Backend enforces `MAX_CONCURRENT_ANALYSES = 2` via an in-memory slot manager.
   - If both slots are saturated, the backend returns HTTP 503 with a `Retry-After: 5` header.
   - The iOS app must implement polite backoff when encountering HTTP 503.
5. **Rate Limiting:**
   - `/api/analyze` is limited to **10 requests per minute** per user ID.
   - `/api/auth/*` is limited to **20 requests per minute** per IP address.
   - Rate limit violations return HTTP 429 with `Retry-After` headers.
6. **Strict Upload Bounds:**
   - Image maximum size: **10 MB** (`.jpg`, `.jpeg`, `.png`, `.webp`). Magic byte validation enforced.
   - Audio maximum size: **25 MB** (`.wav`, `.mp3`, `.webm`, `.ogg`, `.m4a`). Magic byte validation enforced.
   - Audio clips count: Maximum **5 clips** per submission.
   - Symptom text: Maximum **4,000 characters**.
7. **Verdict Heuristic Classification:**
   - The backend returns the complete LLM response in `summary_card.llm_output`.
   - The frontend parses the first 250 characters of `llm_output` to determine whether the verdict styling should be **Danger** (contains *"not suitable"*, *"not appropriate"*, *"mismatch"*), **Success** (contains *"suitable"*, *"appropriate"*, *"match"*), or **Warning** (fallback).
   - The iOS application should adopt this exact parsing contract to ensure consistent visual indicators.

---

## 6. Non-Regression Mandate for iOS Development

The existing web application is fully functional and serving users today. Under no circumstances may any backend endpoint, database model, or configuration setting be modified in a manner that degrades or alters web behavior.

All iOS-specific networking, state management, and asset handling must be implemented as additive, isolated client-side code in `ios/`.

