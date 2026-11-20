# MediScanAI — Testing, Security & Website Non-Regression Audit

**Document:** `mediscanai-app-spec/07_TESTING_SECURITY_NON_REGRESSION_AUDIT.md`  
**Status:** Complete Audit & Verification Framework  
**Scope:** Website Non-Regression Gate, Test Suite Baselines, Mobile Security Hardening, and Risk Matrix  
**Baseline Verification:** Verified on `main` branch (@ `776390e`)

---

## 1. The Website Non-Regression Mandate

The primary operational constraint of the MediScanAI iOS initiative is that **the existing web application, its backend services, database schemas, and AI pipeline must remain 100% operational, undisturbed, and behaviorally unchanged**.

The native iOS client is strictly an **additive client** consuming existing public endpoints. It must not require breaking changes to API schemas, router paths, database models, or backend configuration.

### Non-Regression Definition of Done
A code change is classified as a regression and immediately rejected if it:
1. Breaks or causes compile errors during `cd frontend && npm run build`.
2. Introduces new linting errors in `cd frontend && npm run lint`.
3. Alters the JSON schema or HTTP status codes of any endpoint consumed by `frontend/src/`.
4. Degrades or breaks any of the 32 automated backend API, database, or E2E smoke tests.
5. Inadvertently exposes internal Docker or PostgreSQL ports to the public network.

---

## 2. Baseline Test Suite Results & Non-Regression Gate

Before any iOS code is committed to the repository, the following baseline test suites were executed and verified:

### 2.1 Backend Deterministic Test Suite
- **Command:** `pytest tests/unit tests/api tests/database tests/test_e2e_smoke.py -v`
- **Baseline Result:** **32 passed in 0.02s (100% pass rate)**.
- **Test Categories Covered:**
  - `tests/api/test_analyses_api.py`: Text analysis, unauthenticated rejection, concurrency limit (503), Ollama failure handling, error slot releases, tenant isolation.
  - `tests/api/test_auth_api.py`: Valid registration, duplicate email rejection, malformed email, short password, valid login, invalid password, inactive user check, JWT token verification (`/api/auth/me`), expired token rejection, forged signature rejection.
  - `tests/api/test_health_and_readiness.py`: Root health ping, liveness probe (`/api/health`), readiness probe (`/api/ready`), database disconnect handling, model pre-warming failure handling, startup abort checks.
  - `tests/database/test_database_postgres.py`: PostgreSQL connection, JSON data storage, rollback on integrity violations.
  - `tests/database/test_database_sqlite.py`: SQLite unit fallback, user creation, cascade deletion on analyses, audit log foreign key nullability on user deletion.
  - `tests/test_e2e_smoke.py`: End-to-end user registration, login, profile check, and analysis creation.

### 2.2 Frontend Build & Static Analysis Gate
- **Production Build:**
  - Command: `cd frontend && npm run build`
  - Output: `✓ 2055 modules transformed. dist/index.html (0.99 kB), dist/assets/index.js (397.44 kB), dist/assets/index.css (49.76 kB). Built in 180ms.`
  - Threshold: Must exit code 0 with 0 errors.
- **Linter (Oxlint 1.75.0):**
  - Command: `cd frontend && npm run lint`
  - Output: `Found 11 warnings and 0 errors. Finished in 34ms.`
  - Threshold: Must maintain 0 errors. Warnings must not increase.

---

## 3. Mobile Security & Compliance Audit

### 3.1 Credential & Secret Management
| Asset / Credential | Security Requirement | Storage Implementation |
| :--- | :--- | :--- |
| **JWT Access Token** | Hardware-backed secure storage | Apple Keychain (`kSecClassGenericPassword`) |
| **User Password** | Salted hashing; never plaintext | Client passes in TLS body; backend hashes with `bcrypt` |
| **Google Gemini API Key** | Server-side only; zero client exposure | Server `.env` (`GEMINI_API_KEY`); never sent to iOS client |
| **Groq API Key** | Server-side only; zero client exposure | Server `.env` (`GROQ_API_KEY`); never sent to iOS client |
| **PostgreSQL Passwords** | Local Docker network isolation | Server `.env` (`DATABASE_URL`); port 5432 closed to LAN |
| **Database Connection Strings** | Never embedded in mobile binary | Absent from iOS project configuration |

### 3.2 Transport Security & App Transport Security (ATS)
- **Constraint:** In local development, the backend is reachable via plain HTTP over local Wi-Fi (e.g. `http://192.168.1.100:8000`).
- **Approved ATS Configuration:**
  ```xml
  <key>NSAppTransportSecurity</key>
  <dict>
      <key>NSAllowsLocalNetworking</key>
      <true/>
  </dict>
  ```
- **Security Justification:** `NSAllowsLocalNetworking: true` permits local subnet communication without opening arbitrary external HTTP traffic, satisfying Apple security guidelines.

### 3.3 Sensor Privacy & Permissions
In accordance with Apple App Store Review Guidelines, any hardware sensor access must be preceded by explicit justification strings in `Info.plist`:

```xml
<!-- Camera Access Justification -->
<key>NSCameraUsageDescription</key>
<string>MediScanAI uses your camera exclusively to capture medicine packaging labels for text recognition and clinical analysis. Photos are never shared or sold.</string>

<!-- Microphone Access Justification -->
<key>NSMicrophoneUsageDescription</key>
<string>MediScanAI uses your microphone solely to record voice descriptions of your symptoms for automated transcription. Audio recordings are deleted immediately after analysis.</string>

<!-- Photo Library Access -->
<key>NSPhotoLibraryUsageDescription</key>
<string>MediScanAI allows you to select packaging photos from your library to analyze medication labels.</string>
```

### 3.4 Apple Privacy Manifest (`PrivacyInfo.xcprivacy`)
iOS 17+ requires an explicit privacy manifest detailing data categories collected:
- **Health Data:** Processed in transit; data minimized in PostgreSQL; zero third-party tracking.
- **User Identifiers:** Email address collected for authentication.
- **Tracking:** `NSPrivacyTracking: false` (Zero tracking domains).

---

## 4. Technical Risk Matrix & Mitigation Strategies

| Risk Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **1. Accidental Website Regression**<br>Modifying backend routes or Pydantic models to fit iOS breaks web client. | Critical | Low | Enforce the Non-Regression Gate: any PR touching `backend/` must run `frontend` build and test suites before merge. Default to additive API changes only. |
| **2. Concurrency Saturation (503)**<br>Simultaneous web and iOS analysis requests exceed `MAX_CONCURRENT_ANALYSES = 2`. | High | Medium | iOS client handles HTTP 503 with a calm status screen and respects the `Retry-After: 5` header without crashing or spamming retries. |
| **3. Local Wi-Fi Disconnect**<br>iPhone switches from Wi-Fi to cellular data, losing connection to MacBook IP. | High | High | Implement local connection probing (`GET /api/health`) with immediate user-friendly notification: *"iPhone not on same Wi-Fi as host Mac"*. |
| **4. Insecure Token Storage**<br>Developer mistakenly uses `UserDefaults` for session persistence. | High | Low | Enforce `KeychainStorage` via code review and static analysis; write dedicated unit tests verifying Keychain read/write/delete. |
| **5. Oversized Media Uploads**<br>iPhone 48MP ProRAW photos exceed the 10 MB backend upload limit. | Medium | High | Implement on-device image downsampling in `ImageCompressor.swift` to ensure uploaded JPEG payloads never exceed 8 MB. |
| **6. Emergency Patient Presentation**<br>User inputs acute symptoms (e.g. crushing chest pain). | Critical | Low | Verified backend Emergency Triage Guardrail fast-paths immediate 112/911 emergency directives in under 10 ms; iOS UI renders bold red alert banner. |

---

## 5. Non-Regression Sign-Off Checklist

Before any release or branch merge, the engineer must verify:
- [ ] `cd frontend && npm run build` passes with exit code 0.
- [ ] `cd frontend && npm run lint` passes with 0 errors.
- [ ] `pytest tests/unit tests/api tests/database tests/test_e2e_smoke.py` passes 32/32 tests.
- [ ] Docker Compose production deployment starts cleanly (`docker compose up -d`).
- [ ] Web application at `http://localhost:5173` successfully completes login, scan, symptom analysis, and history deletion.
- [ ] iOS application builds cleanly in Xcode with zero compilation warnings.

