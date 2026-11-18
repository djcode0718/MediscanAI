# MediScanAI iOS — Master Implementation & Local-Network Verification Checklist

**Document Version:** 1.0.0  
**Project:** MediScanAI Native iOS Client (`ios/MediScanAI`)  
**Target Platform:** iOS 17.0+ (Swift 5.10 / 6.0, SwiftUI)  
**Host Backend Target:** MacBook Air M4 (Local Wi-Fi Subnet)  
**Author:** Senior iOS Architect, Backend Engineer, Network Engineer & QA Lead  
**Baseline Repository State:** `main` branch @ commit `776390e`  
**Governing Rule:** 100% additive isolation inside `ios/`; zero code or schema changes to the existing web application, backend, database, or AI pipeline.

---

## Progress Dashboard

| Metric | Count | Percentage | Definition |
| :--- | :---: | :---: | :--- |
| **Total Implementation Tasks** | **92** | 100.0% | Active scope (Phase 1 through Phase 11). Excludes Phase 0 and deferred Phase 12. |
| **Completed & Verified Tasks `[x]`** | **38** | **41.3%** | Concrete implementation code exists and is empirically verified in `ios/MediScanAI/`. |
| **In Progress Tasks `[-]`** | **0** | **0.0%** | Currently active tasks. |
| **Blocked Tasks `[!]`** | **0** | **0.0%** | Tasks blocked by architectural or environmental impediments. |
| **Remaining Tasks `[ ]`** | **54** | **58.7%** | Scheduled for execution across Phases 6–11. |
| **Phase 0 Discovery Tasks (Audit Baseline)** | **14 / 14** | **100.0%** | Pre-implementation discovery & architectural specifications completed. |
| **Future Enhancements (Deferred)** | **5** | — | Remote Tailscale connectivity tasks (explicitly excluded from initial milestone). |

*Counting Methodology:* Completion metrics track actual Swift/Xcode implementation code. Completed Phase 0 audit documents are tracked separately in Section 2 and are not counted toward the code implementation progress. Tasks SCAF-01 through SCAF-07 (Phase 1), DSGN-01 through DSGN-10 (Phase 2), NET-01 through NET-09 (Phase 3), AUTH-01 through AUTH-07 (Phase 4), and WIFI-01 through WIFI-05 (Phase 5) represent 41.3% of the 92 active tasks.

---

## Section 1 — Project Governance, Safety & Non-Regression Gates

All implementation work is subject to these non-negotiable boundaries:

- [ ] `GOV-01`: **Additive-Only Directory Isolation**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* All iOS application code, assets, project files, and tests must reside strictly inside `ios/`. Zero files outside `ios/` may be added or modified, except explicitly approved documentation updates in `mediscanai-app-spec/`.  
  - *Verification Method:* `git status --porcelain` and `git diff --stat origin/main` show modifications exclusively in `ios/` and `mediscanai-app-spec/`.  
  - *Status:* `[ ]` Not Started

- [ ] `GOV-02`: **Git Safety & Working Tree Preservation**  
  - *Dependencies:* `GOV-01`  
  - *Acceptance Criteria:* Development occurs on a dedicated feature branch branched from `main`. Commits must be atomic, focused, and tested. No destructive Git operations (`git reset --hard`, `git push --force`, `git clean -fd`) are permitted.  
  - *Verification Method:* `git branch --show-current` confirms isolated branch; `git log --oneline -n 5` confirms atomic commit history.  
  - *Status:* `[ ]` Not Started

- [ ] `GOV-03`: **Website Non-Regression Gate Enforcement**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* Before and after any development milestone, the existing web frontend and backend test suites must be executed. Web build must exit code 0; web linter must report 0 errors and no more than 11 warnings; backend tests must pass without failures.  
  - *Verification Method:* Execute mandatory verification commands:  
    `cd frontend && npm run build` (Exit 0)  
    `cd frontend && npm run lint` (0 errors, ≤ 11 warnings)  
    `pytest tests/api tests/database tests/test_e2e_smoke.py -v`  
  - *Status:* `[ ]` Not Started

- [ ] `GOV-04`: **API Contract Immutability**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* The existing FastAPI route paths, HTTP methods, Pydantic request/response schemas, error payloads, and status codes must remain strictly unchanged. The iOS app adapts to the backend, never vice versa.  
  - *Verification Method:* Code review of all Git diffs to ensure zero modifications to `backend/api/`, `backend/schemas/`, or `backend/main.py`.  
  - *Status:* `[ ]` Not Started

- [ ] `GOV-05`: **Database & Data Minimization Protection**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* Zero modifications to SQLAlchemy ORM models (`backend/models/`) or Alembic migrations (`alembic/versions/`). PostgreSQL port 5432 remains unexposed to the LAN. Raw images and audio clips are never persisted on device storage or server database.  
  - *Verification Method:* Verify PostgreSQL port binding is isolated; inspect mobile data sandbox to confirm media is purged post-upload.  
  - *Status:* `[ ]` Not Started

- [ ] `GOV-06`: **Zero-Cost & Local Privacy Mandate**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* Infrastructure cost remains ₹0/month. No paid cloud APIs, external paid speech engines, or paid database hosting may be introduced. Online LLM fallbacks remain strictly within free tiers (Gemini Flash, Groq OSS).  
  - *Verification Method:* Audit all network calls to ensure zero billable API endpoints are accessed.  
  - *Status:* `[ ]` Not Started

---

## Section 2 — Phase 0: Discovery, Network Verification & Technical Baseline

*Objective:* Verify the actual repository runtime, reconcile backend binding discrepancies, determine Mac LAN reachability, and document technical baselines.

- [x] `DISC-01`: **Website Functional & Architectural Audit**  
  - *Deliverable:* `mediscanai-app-spec/01_EXISTING_PRODUCT_AUDIT.md`  
  - *Verified Facts:* React 19.2.8 + Vite 8.2.2; 6 user journeys; full multimodal composer; history slide-over; 10MB image cap; 25MB audio cap; 4000 char text cap.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-02`: **FastAPI Backend Route & Schema Inventory**  
  - *Deliverable:* `mediscanai-app-spec/02_BACKEND_API_AUDIT.md`  
  - *Verified Facts:* 10 endpoints; Bearer JWT auth (60 min expiry); `/api/analyze` accepts multipart `text`, `image`, `audio`; rate limit 10/min (429); concurrency max 2 slots (503).  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-03`: **Multimodal AI Pipeline & Inference Audit**  
  - *Deliverable:* `mediscanai-app-spec/03_AI_PIPELINE_AUDIT.md`  
  - *Verified Facts:* PaddleOCR (OpenMP pre-warming required); Faster-Whisper base CPU int8; FAISS + BM25 + Cross-Encoder retrieval; 4-tier zero-cost online fallback chain (Gemini 3.6/3.7 Flash → Groq OSS 120B/20B); 112/911 emergency fast-path triage.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-04`: **Database, Authentication & Data Minimization Audit**  
  - *Deliverable:* `mediscanai-app-spec/04_DATABASE_AUTH_DATA_AUDIT.md`  
  - *Verified Facts:* PostgreSQL 15 `users`, `analyses`, `audit_logs` (Alembic 0001–0003); bcrypt password hashing; stateless JWT; data minimization strictly enforced (raw files unlinked post-inference).  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-05`: **iOS Architecture & Networking Recommendation**  
  - *Deliverable:* `mediscanai-app-spec/05_IOS_ARCHITECTURE_RECOMMENDATION.md`  
  - *Verified Facts:* SwiftUI iOS 17+, typed URLSession, Keychain storage, local Wi-Fi connectivity (`NSAllowsLocalNetworking: true`), AVFoundation camera and microphone services.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-06`: **iOS UI/UX Design System & Screen Specifications**  
  - *Deliverable:* `mediscanai-app-spec/06_IOS_UI_UX_DESIGN_RECOMMENDATION.md`  
  - *Verified Facts:* True-black OLED foundation (`#000000`), monochromatic tokens (`#0A0A0A` to `#262626`), SF Pro Dynamic Type, 4pt spacing scale, 8 screen specs, semantic status accents (Red/Green/Amber).  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-07`: **Testing, Security & Non-Regression Framework**  
  - *Deliverable:* `mediscanai-app-spec/07_TESTING_SECURITY_NON_REGRESSION_AUDIT.md`  
  - *Verified Facts:* Hard non-regression gate commands; baseline build in 180ms; Oxlint 0 errors; mobile security matrix; ATS exception scoping.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-08`: **Implementation Readiness & Phased Roadmap**  
  - *Deliverable:* `mediscanai-app-spec/08_IMPLEMENTATION_READINESS_REPORT.md`  
  - *Verified Facts:* Formal GO determination; 11-phase implementation plan (Phase 0–Phase 10) with milestones and exit criteria.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-09`: **Reconciled Product Requirements Document**  
  - *Deliverable:* `mediscanai-app-spec/MediScanAI_iOS_PRD_Tech_Spec.md`  
  - *Verified Facts:* Reconciled with verified backend routes, upload limits, resolved discovery items, and data retention policies.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-10`: **Reconciled UI/UX Design Document**  
  - *Deliverable:* `mediscanai-app-spec/MediScanAI_iOS_Design_Document.md`  
  - *Verified Facts:* Reconciled with approved design system tokens, 4-tab native navigation, screen layouts, and component signatures.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-11`: **Master Technical Audit Index**  
  - *Deliverable:* `mediscanai-app-spec/AUDIT_INDEX.md`  
  - *Verified Facts:* Master navigation guide, reading order, and engineering summary.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-12`: **Actual Local-Network Binding Discrepancy Verification**  
  - *Verified Facts:*  
    1. Direct macOS execution (`start.sh` line 136 and `backend/main.py` line 558) binds to `127.0.0.1:8000`. This is **loopback-only** and CANNOT be reached by an iPhone on the LAN. Direct host execution requires `--host 0.0.0.0 --port 8000` to be accessible from local Wi-Fi.  
    2. Local Development Docker Compose (`docker-compose.yml`) binds container Uvicorn to `0.0.0.0:8000` and publishes `ports: - "8000:8000"` to host `0.0.0.0:8000`. This **IS reachable** from the LAN at `http://<Mac-LAN-IP>:8000`. (Warning: Postgres port 5432 is also published in this compose file).  
    3. Production Docker Compose (`deployment/docker-compose.prod.yml`) binds backend internally to `0.0.0.0:8000` via `expose: - "8000"`, isolates Postgres (`expose: - "5432"`), and routes external traffic through Caddy on ports `80` and `443`. This **IS reachable** from the LAN at `http://<Mac-LAN-IP>:80`.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-13`: **Mac LAN Interface & Reachability Inspection**  
  - *Verified Facts:* Active Wi-Fi interface is `en0`; current private LAN IPv4 address is `192.168.0.155` (dynamic DHCP subnet `192.168.0.0/24`); macOS Application Firewall is disabled (`socketfilterfw --getglobalstate` reports State = 0); host ports 80, 443, 8000, 5432 are currently unallocated.  
  - *Status:* `[x]` Completed and verified

- [x] `DISC-14`: **CORS & Native URLSession Contract Verification**  
  - *Verified Facts:* Native iOS `URLSession` does NOT enforce browser Cross-Origin Resource Sharing (CORS) and does NOT issue HTTP `OPTIONS` preflight requests. Backend `CORSMiddleware` in `backend/main.py` will not interfere with native Swift requests. Bearer JWT authentication via `Authorization: Bearer <token>` is fully supported on all protected routes.  
  - *Status:* `[x]` Completed and verified

---

## Section 3 — Phase 1: Xcode Project Scaffolding & Setup

*Objective:* Create a clean, buildable native iOS project in `ios/MediScanAI` targeting iOS 17.0+ with modern Swift 5.10 / 6.0 settings and security manifests.

- [x] `SCAF-01`: **Directory Scaffolding**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* Create directory tree: `ios/MediScanAI/App`, `Core/{Networking,Authentication,DesignSystem,Media,Utilities}`, `Features/{Auth,Home,Scan,Symptoms,Analysis,History,Profile}`, `Resources`, and test directories `MediScanAITests`, `MediScanAIUITests`.  
  - *Verification Method:* Verified directory tree layout with `.gitkeep` placeholders; matches clean architectural structure.  
  - *Status:* `[x]` Completed and verified

- [x] `SCAF-02`: **Xcode Project Initialization**  
  - *Dependencies:* `SCAF-01`  
  - *Acceptance Criteria:* Initialize `MediScanAI.xcodeproj` with target `MediScanAI`, Swift 5.10/6.0 compatibility mode, SwiftUI interface, iOS 17.0 deployment target, and bundle identifier `ai.mediscan.ios`.  
  - *Verification Method:* `xcodebuild -project ios/MediScanAI/MediScanAI.xcodeproj -scheme MediScanAI -destination "generic/platform=iOS Simulator" build` succeeded with exit code 0.  
  - *Status:* `[x]` Completed and verified

- [x] `SCAF-03`: **Test Target Configuration**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Configure unit test target (`MediScanAITests`) and UI test target (`MediScanAIUITests`) linked to main application target.  
  - *Verification Method:* `xcodebuild test -project ios/MediScanAI/MediScanAI.xcodeproj -scheme MediScanAI -destination "platform=iOS Simulator,name=iPhone 16 Pro"` executed and passed 3/3 unit tests and 1/1 UI launch test with exit code 0.  
  - *Status:* `[x]` Completed and verified

- [x] `SCAF-04`: **App Transport Security (ATS) Configuration**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* In `Info.plist`, configure `NSAppTransportSecurity` with `NSAllowsLocalNetworking: true` to permit plain HTTP to private LAN subnets while keeping all external internet traffic locked to HTTPS.  
  - *Verification Method:* Inspected `ios/MediScanAI/MediScanAI/Info.plist`; confirmed `NSAllowsLocalNetworking: true` is present and `NSAllowsArbitraryLoads` is strictly absent.  
  - *Status:* `[x]` Completed and verified

- [x] `SCAF-05`: **Local Network & Sensor Privacy Declarations**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Add clear, clinical justification strings in `Info.plist` for `NSCameraUsageDescription`, `NSMicrophoneUsageDescription`, and `NSLocalNetworkUsageDescription`.  
  - *Verification Method:* Verified strings in `Info.plist` detailing private local analysis without external third-party sharing.  
  - *Status:* `[x]` Completed and verified

- [x] `SCAF-06`: **Apple Privacy Manifest (`PrivacyInfo.xcprivacy`)**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Create `PrivacyInfo.xcprivacy` declaring zero tracking domains (`NSPrivacyTracking: false`) and empty required-reason APIs for foundation phase.  
  - *Verification Method:* Verified syntactically valid XML property list at `ios/MediScanAI/MediScanAI/PrivacyInfo.xcprivacy`.  
  - *Status:* `[x]` Completed and verified

- [x] `SCAF-07`: **Application Entry Point & Coordinator Scaffolding**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Implement `@main struct MediScanAIApp: App`, `AppCoordinator`, and `AppEnvironment` dependency container with true-black `#000000` minimal launch screen.  
  - *Verification Method:* `MediScanAIUITests.testLaunchAndFoundationScreenVisible` verified app launch, branding static text `"MediScanAI"`, and placeholder subtitle on iPhone 16 Pro Simulator.  
  - *Status:* `[x]` Completed and verified

---

## Section 4 — Phase 2: Design System & Monochromatic OLED Components

*Objective:* Implement the approved true-black design system, monochromatic color tokens, San Francisco Dynamic Type, and reusable SwiftUI components.

- [x] `DSGN-01`: **Color Token Palette Implementation**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Define `Color` extension with exact tokens: `background (#000000)`, `surfacePrimary (#0A0A0A)`, `surfaceSecondary (#141414)`, `surfaceTertiary (#1E1E1E)`, `surfaceElevated (#262626)`, `borderSubtle (#2A2A2A)`, `borderFocus (#404040)`, `textPrimary (#FFFFFF)`, `textSecondary (#A1A1A1)`, `textTertiary (#707070)`.  
  - *Verification Method:* Verified `AppColors.swift` with hex parsing and token constants; validated by `DesignSystemTests.testMonochromaticHexConstants` and `testColorHexParsing`; previewed in `DesignSystemPreviewView`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-02`: **Semantic Status Accents**  
  - *Dependencies:* `DSGN-01`  
  - *Acceptance Criteria:* Implement semantic color tokens for clinical verdicts: `statusDanger (#F43F5E, fill #2D0A14, border #5C1D2C)`, `statusSuccess (#10B981, fill #06281E, border #0D5C45)`, and `statusWarning (#F59E0B, fill #2E1E05, border #5C4010)`.  
  - *Verification Method:* Validated by `DesignSystemTests.testSemanticStatusHexConstants` and visual inspection in `DesignSystemPreviewView`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-03`: **Typography Scale & Dynamic Type Modifiers**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Implement view modifiers for SF Pro type styles: `largeTitle (34pt bold)`, `title1 (28pt semibold)`, `title2 (22pt semibold)`, `title3 (20pt medium)`, `headline (17pt semibold)`, `body (17pt regular)`, `callout (16pt regular)`, `subheadline (15pt regular)`, `footnote (13pt regular)`, `caption1 (12pt medium)`. Support tabular figures (`.monospacedDigit()`).  
  - *Verification Method:* Verified `AppTypography.swift` with tracking, lineSpacing, and `.monospacedDigit()` modifiers; displayed in `DesignSystemPreviewView` typography section.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-04`: **Spacing & Corner Radius System**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Define constants for 4pt spacing scale (`4, 8, 12, 16, 20, 24, 32, 48pt`) and radii (`8pt, 12pt, 16pt, 24pt, 999pt`).  
  - *Verification Method:* Verified `AppSpacing.swift` and `AppRadius.swift`; verified by `DesignSystemTests.testSpacingScaleConstants` and `testCornerRadiiConstants`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-05`: **Reusable Button Components**  
  - *Dependencies:* `DSGN-01`, `DSGN-03`  
  - *Acceptance Criteria:* Implement `PrimaryButton` (inverted white fill `#FFFFFF`, black text `#000000`, 12pt radius, 0.98 scale pressed state), `SecondaryButton` (`#1E1E1E` fill, `#2A2A2A` border), `DestructiveButton`, and `IconButton`.  
  - *Verification Method:* Interactive preview in `DesignSystemPreviewView` and automated UI tap test in `DesignSystemUITests.testDesignSystemPreviewRendersDirectly`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-06`: **Surface & Container Views**  
  - *Dependencies:* `DSGN-01`, `DSGN-04`  
  - *Acceptance Criteria:* Implement `SurfaceCard` with `#141414` background, `#2A2A2A` border, 16pt radius, and 16pt interior padding, including interactive variants.  
  - *Verification Method:* Verified `AppCard.swift` and `InteractiveAppCard`; verified rendering in `DesignSystemPreviewView`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-07`: **Form Input Components**  
  - *Dependencies:* `DSGN-01`, `DSGN-04`  
  - *Acceptance Criteria:* Implement `TextInputField` and `MultilineInputField` with `#141414` fill, `#2A2A2A` subtle border, `#404040` active focus ring, clear placeholder, secure entry toggle, and inline error support.  
  - *Verification Method:* Verified `AppTextField.swift` and `AppTextEditor`; verified live binding and validation rendering in `DesignSystemPreviewView`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-08`: **Verdict & Status Indicators**  
  - *Dependencies:* `DSGN-02`  
  - *Acceptance Criteria:* Implement `VerdictBadge` (Danger / Success / Caution pill), `MediaChip`, and `StatusIndicator` (dual-concentric white ring spinner with pulse animation and staged loading view).  
  - *Verification Method:* Validated by `DesignSystemTests.testClinicalVerdictStatusMapping` and animated rendering in `DesignSystemPreviewView`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-09`: **Notice & Disclaimer Banners**  
  - *Dependencies:* `DSGN-01`, `DSGN-02`  
  - *Acceptance Criteria:* Implement `NoticeBanner` for medical disclaimers and emergency alerts (call 112/911).  
  - *Verification Method:* Validated by `DesignSystemTests.testNoticeBannerVariants` and verified rendering in `DesignSystemPreviewView`.  
  - *Status:* `[x]` Completed and verified

- [x] `DSGN-10`: **Haptic Feedback Controller**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Implement `HapticFeedback` wrapper providing `impact(.medium)` for shutter, `impact(.soft)` for recording, `notification(.success)` for completed analysis, and `notification(.warning)` for danger verdicts.  
  - *Verification Method:* Verified `HapticFeedback.swift` with UIKit impact/notification generator wrappers; integrated into button taps and banner action callbacks.  
  - *Status:* `[x]` Completed and verified

---

## Section 5 — Phase 3: Networking Foundation & Typed API Client

*Objective:* Build an async/await `URLSession` client with streaming multipart/form-data support, robust error mapping, and health/readiness probe integration.

- [x] `NET-01`: **API Endpoint Taxonomy**
  - *Dependencies:* `SCAF-02`
  - *Acceptance Criteria:* Implement type-safe `APIEndpoint` enum covering all backend routes (`health`, `ready`, `authRegister`, `authLogin`, `authMe`, `analyze`, `analysesList`, `analysisDetail`, `analysisDelete`).
  - *Verification Method:* Verified in `APIEndpoint.swift`; validated by `NetworkingTests.testAPIEndpointTaxonomyAndURLs` verifying HTTP methods, relative paths, timeout intervals (15s standard, 120s analyze), query item parameters, and auth requirements.
  - *Status:* `[x]` Completed and verified

- [x] `NET-02`: **Server Configuration Manager**
  - *Dependencies:* `NET-01`
  - *Acceptance Criteria:* Implement `NetworkConfiguration` storing the user-configurable base URL (default: `http://192.168.0.155:8000`), persisting to `UserDefaults`, validating scheme and host, and stripping trailing slashes.
  - *Verification Method:* Verified in `NetworkConfiguration.swift`; validated by `NetworkingTests.testNetworkConfigurationNormalizationAndDefaults`.
  - *Status:* `[x]` Completed and verified

- [x] `NET-03`: **JSON Request & Response Pipeline**
  - *Dependencies:* `NET-01`
  - *Acceptance Criteria:* Implement typed `send<T: Decodable>(_ endpoint: APIEndpoint, responseType: T.Type)` method on `NetworkClient` using `NetworkTransport` with ISO8601 custom date decoding strategy (handling fractional seconds and Unix timestamps).
  - *Verification Method:* Verified in `NetworkClient.swift`; validated by `NetworkingTests.testUserResponseAndTokenResponseDecoding` and `testAnalysisResultResponseDecoding`.
  - *Status:* `[x]` Completed and verified

- [x] `NET-04`: **Multipart/Form-Data Encoder**
  - *Dependencies:* `NET-01`
  - *Acceptance Criteria:* Implement `MultipartFormDataEncoder` supporting `text` (form field), `image` (file part with MIME type), and repeated `audio` (file parts with MIME type) using unique boundaries, enforcing backend constraints (max 4000 char text, max 10MB image, max 25MB audio, max 5 audio clips, empty submission rejection).
  - *Verification Method:* Verified in `MultipartFormDataEncoder.swift`; validated by `NetworkingTests.testMultipartFormDataEncoderEncodingAndValidation` testing constraints and RFC 7578 formatting.
  - *Status:* `[x]` Completed and verified

- [x] `NET-05`: **Correlation ID Injection**
  - *Dependencies:* `NET-03`
  - *Acceptance Criteria:* Inject unique `X-Request-ID` UUID header into every outgoing request; read returned `X-Request-ID` from response headers for logging.
  - *Verification Method:* Verified in `NetworkClient.swift`; validated by `NetworkingTests.testCorrelationIDHeaderInjection`.
  - *Status:* `[x]` Completed and verified

- [x] `NET-06`: **Network Error Mapping**
  - *Dependencies:* `NET-03`
  - *Acceptance Criteria:* Implement `APIError` enum decoding HTTP status codes: `400 (badRequest)`, `401 (unauthorized)`, `403 (forbidden)`, `404 (notFound)`, `422 (unprocessableEntity)`, `429 (rateLimited with Retry-After)`, `503 (serviceUnavailable with Retry-After)`, `500...599 (serverError)`, `timeout`, `noConnection`, `invalidURL`, `cancelled`.
  - *Verification Method:* Verified in `APIError.swift`; validated by `NetworkingTests.testErrorMappingFromStatusCodes`.
  - *Status:* `[x]` Completed and verified

- [x] `NET-07`: **Timeout & Cancellation Policy**
  - *Dependencies:* `NET-03`
  - *Acceptance Criteria:* Configure 15s timeout for standard auth/history requests; 120s timeout for heavy multimodal analysis requests; cooperative cancellation support via Swift `Task.checkCancellation()`.
  - *Verification Method:* Verified in `APIEndpoint.timeoutInterval` and `NetworkClient.swift`; validated by `NetworkingTests.testAPIEndpointTaxonomyAndURLs`.
  - *Status:* `[x]` Completed and verified

- [x] `NET-08`: **Health Probe Integration**
  - *Dependencies:* `NET-02`, `NET-03`
  - *Acceptance Criteria:* Implement `checkHealth()` pinging `GET /api/health` returning latency in milliseconds and server status.
  - *Verification Method:* Verified in `NetworkClient.checkHealth()`; validated by `NetworkingTests.testHealthProbeExecution`.
  - *Status:* `[x]` Completed and verified

- [x] `NET-09`: **Readiness Probe Integration**
  - *Dependencies:* `NET-03`
  - *Acceptance Criteria:* Implement `checkReadiness()` pinging `GET /api/ready` returning database, model loading, OCR pre-warming, and slot capacity metrics.
  - *Verification Method:* Verified in `NetworkClient.checkReadiness()`; validated by `NetworkingTests.testReadinessProbeExecution`.
  - *Status:* `[x]` Completed and verified

---

## Section 6 — Phase 4: Authentication & Secure Session Management

*Objective:* Implement Keychain-backed JWT credential storage, user registration, login, profile retrieval, and automatic session expiration handling.

- [x] `AUTH-01`: **Keychain Storage Service**
  - *Dependencies:* `SCAF-02`
  - *Acceptance Criteria:* Implement `KeychainStorage` wrapping Apple Keychain Services (`kSecClassGenericPassword`, `kSecAttrAccessibleAfterFirstUnlock`) for storing, retrieving, and wiping the JWT access token. Provide `MockKeychainStorage` for tests.
  - *Verification Method:* Verified in `KeychainStorage.swift`; validated by `AuthenticationTests.testMockKeychainSaveAndRetrieve`, `testMockKeychainOverwriteToken`, `testMockKeychainDeleteToken`, `testMockKeychainErrorPropagation`, and `testRealKeychainStorageInitialization`.
  - *Status:* `[x]` Completed and verified

- [x] `AUTH-02`: **Auth State Machine & Session Coordinator**
  - *Dependencies:* `AUTH-01`, `NET-03`
  - *Acceptance Criteria:* Implement `@Observable class AuthManager` with states: `.unauthenticated`, `.authenticating`, `.authenticated(UserSession)`. Expose `currentUser`, `isAuthenticated`, and coordinate with `AuthorizationHeaderProviding`.
  - *Verification Method:* Verified in `UserSession.swift` and `AuthManager.swift`; validated by `AuthenticationTests.testAuthManagerInitialState` and `testExplicitLogoutClearsStateAndKeychain`.
  - *Status:* `[x]` Completed and verified

- [x] `AUTH-03`: **User Registration Flow**
  - *Dependencies:* `AUTH-02`
  - *Acceptance Criteria:* Implement `register(email, password, fullName)` calling `POST /api/auth/register`. On 201 Created, save access token to Keychain, set user state, and transition to `.authenticated`. Enforce minimum 6 characters for password.
  - *Verification Method:* Verified in `AuthManager.register`; validated by `AuthenticationTests.testRegisterSuccessPersistsTokenAndUpdatesState` and `testRegisterFailureThrowsBadRequest`.
  - *Status:* `[x]` Completed and verified

- [x] `AUTH-04`: **User Login Flow**
  - *Dependencies:* `AUTH-02`
  - *Acceptance Criteria:* Implement `login(email, password)` calling `POST /api/auth/login`. On 200 OK, persist token to Keychain, update user profile, and transition to `.authenticated`. Throw `APIError.unauthorized` on 401.
  - *Verification Method:* Verified in `AuthManager.login`; validated by `AuthenticationTests.testLoginSuccessPersistsTokenAndUpdatesState` and `testLoginFailureThrowsErrorAndClearsState`.
  - *Status:* `[x]` Completed and verified

- [x] `AUTH-05`: **Session Restoration on App Launch**
  - *Dependencies:* `AUTH-02`
  - *Acceptance Criteria:* On app startup, read token from Keychain; if present, call `GET /api/auth/me`. If 200 OK, restore user session; if 401 Unauthorized, wipe Keychain and transition to `.unauthenticated`.
  - *Verification Method:* Verified in `AuthManager.restoreSession`; validated by `AuthenticationTests.testRestoreSessionWithValidToken`, `testRestoreSessionWithExpiredTokenWipesKeychain`, and `testRestoreSessionWithEmptyKeychain`.
  - *Status:* `[x]` Completed and verified

- [x] `AUTH-06`: **Automatic 401 Interception & Sign-Out**
  - *Dependencies:* `AUTH-02`, `NET-06`
  - *Acceptance Criteria:* When any protected API request encounters HTTP 401, `NetworkClient` triggers `onUnauthorized` to notify `AuthManager` to immediately wipe credentials and route UI to the login screen without duplicate storm triggers.
  - *Verification Method:* Verified in `NetworkClient.executeAndDecode` and `AuthManager.handleUnauthorized`; validated by `AuthenticationTests.testHandleUnauthorizedEvictsSession`.
  - *Status:* `[x]` Completed and verified

- [x] `AUTH-07`: **Sign-In & Sign-Up UI Views**
  - *Dependencies:* `AUTH-03`, `AUTH-04`, `DSGN-05`, `DSGN-07`
  - *Acceptance Criteria:* Implement `LoginView`, `RegisterView`, `AuthenticatedHomePlaceholderView`, and `AuthenticationViewModel` following the true-black design system, with keyboard handling, email validation, and inline error banners.
  - *Verification Method:* Validated by `AuthenticationTests.testAuthenticationViewModelValidation` and end-to-end UI automation in `AuthenticationUITests.testLoginViewElementsPresent` and `testNavigateToRegistrationAndBack`.
  - *Status:* `[x]` Completed and verified

---

## Section 7 — Phase 5: Local Wi-Fi Connectivity & Server Health Probing

*Objective:* Enable dynamic Mac LAN IP configuration, real-time connectivity testing, and user guidance for same-Wi-Fi execution.

- [x] `WIFI-01`: **Server Connection Configuration UI**
  - *Dependencies:* `NET-02`, `DSGN-07`
  - *Acceptance Criteria:* Implement `ServerConfigSheet` allowing the user to view and edit the backend base URL (e.g., `http://192.168.0.155:8000`), with input validation and clear setup tips.
  - *Verification Method:* Verified in `ServerConfigSheet.swift` and `NetworkConfiguration.swift`; validated by `ServerConnectionTests.testValidLocalURLNormalization`, `testInvalidURLDetection`, and `testConfigurationPersistenceAcrossInstances`.
  - *Status:* `[x]` Completed and verified

- [x] `WIFI-02`: **Live Connection Testing Action**
  - *Dependencies:* `WIFI-01`, `NET-08`
  - *Acceptance Criteria:* Provide a "Test Connection" button that calls `checkHealth()`. Displays green checkmark with round-trip latency (e.g., `Connected (14 ms)`) on success, or red warning with diagnostic guidance on failure.
  - *Verification Method:* Verified in `ServerConnectionManager.checkConnection()`; validated by `ServerConnectionTests.testCheckConnectionSuccessReportsLatency`, `testCheckConnectionUnhealthyStatus`, `testCheckConnectionTimeoutError`, and `testCheckConnectionPreventsDuplicateRequests`.
  - *Status:* `[x]` Completed and verified

- [x] `WIFI-03`: **Home Screen Connection Status Badge**
  - *Dependencies:* `WIFI-02`, `DSGN-08`
  - *Acceptance Criteria:* Add a compact status capsule in the Home header: `🟢 Local Wi-Fi` when connected, `🔴 Disconnected` when unreachable. Tapping opens `ServerConfigSheet`.
  - *Verification Method:* Verified in `ServerConnectionBadge.swift`; validated by `ServerConnectionTests.testServerConnectionStatusTaxonomy` and automated UI tap test in `ServerConnectionUITests.testTappingBadgeOpensServerConfigSheetAndDismisses`.
  - *Status:* `[x]` Completed and verified

- [x] `WIFI-04`: **Local Network Permission Prompt Handling**
  - *Dependencies:* `SCAF-05`
  - *Acceptance Criteria:* Handle iOS local network privacy prompt gracefully without crashing or false-positive error alerts. Provide clear guidance on iOS Settings → MediScanAI permissions.
  - *Verification Method:* Verified in `Info.plist` (`NSLocalNetworkUsageDescription`), `ServerConnectionManager.swift`, and `ServerConfigSheet.swift`.
  - *Status:* `[x]` Completed and verified

- [x] `WIFI-05`: **Connection Failure Recovery Screen**
  - *Dependencies:* `WIFI-01`, `DSGN-09`
  - *Acceptance Criteria:* When requests fail due to network loss, display an actionable offline card: *"Cannot reach Mac backend. Ensure your iPhone is on the same Wi-Fi network and the backend is running."*
  - *Verification Method:* Verified in `ConnectionFailureRecoveryView.swift`; validated by `ServerConnectionTests.testUnreachableBackendDoesNotInvalidateUserSession` and integrated into `AuthenticatedHomePlaceholderView`.
  - *Status:* `[x]` Completed and verified

---

## Section 8 — Phase 6: Home Screen & Native Navigation

*Objective:* Implement the 4-tab native navigation container, the home dashboard, quick-action cards, and recent analyses preview.

- [ ] `NAV-01`: **4-Tab Navigation Shell**  
  - *Dependencies:* `DSGN-01`, `AUTH-02`  
  - *Acceptance Criteria:* Implement `MainTabView` containing 4 tabs: `Home` (`house`), `Scan` (`camera.viewfinder`), `History` (`clock`), `Profile` (`person`). Active tab uses `#FFFFFF`; inactive uses `#707070`.  
  - *Verification Method:* SwiftUI preview verifies tab navigation and icon rendering.  
  - *Status:* `[ ]` Not Started

- [ ] `NAV-02`: **Home Dashboard View**  
  - *Dependencies:* `NAV-01`, `DSGN-06`  
  - *Acceptance Criteria:* Implement `HomeView` with brand header, connection status pill, greeting, quick-action cards, and recent history section.  
  - *Verification Method:* SwiftUI preview renders complete home layout.  
  - *Status:* `[ ]` Not Started

- [ ] `NAV-03`: **Quick-Action Cards**  
  - *Dependencies:* `NAV-02`, `DSGN-06`  
  - *Acceptance Criteria:* Implement large hero card: **"Scan Medicine"** (switches to Scan tab or presents camera sheet); secondary cards: **"Enter Symptoms"** (opens symptom composer) and **"Voice Recording"** (opens audio recorder).  
  - *Verification Method:* Tapping each quick action triggers appropriate navigation.  
  - *Status:* `[ ]` Not Started

- [ ] `NAV-04`: **Recent Activity Section**  
  - *Dependencies:* `NAV-02`  
  - *Acceptance Criteria:* Fetch latest 3 analyses; render compact cards with modality badge, verdict headline snippet, and relative timestamp. Empty state displays *"Awaiting First Analysis"*.  
  - *Verification Method:* SwiftUI preview tests populated and empty states.  
  - *Status:* `[ ]` Not Started

---

## Section 9 — Phase 7: Medicine Camera & Packaging Inspection Pipeline

*Objective:* Implement the native camera viewfinder, photo library picker, image compression, preview sheet, and vision analysis execution.

- [ ] `CAM-01`: **AVCaptureSession Camera Service**  
  - *Dependencies:* `SCAF-05`  
  - *Acceptance Criteria:* Implement `CameraService` running `AVCaptureSession` with photo output, video preview layer, pinch-to-zoom, and tap-to-focus.  
  - *Verification Method:* Unit test verifies session configuration; physical device test verifies video preview.  
  - *Status:* `[ ]` Not Started

- [ ] `CAM-02`: **Camera Viewfinder UI**  
  - *Dependencies:* `CAM-01`, `DSGN-01`  
  - *Acceptance Criteria:* Implement `CameraScanView` with fullscreen live preview, corner framing reticles, flashlight toggle, gallery picker button, and high-contrast shutter button.  
  - *Verification Method:* Interactive testing verifies reticle overlay and control layout.  
  - *Status:* `[ ]` Not Started

- [ ] `CAM-03`: **Photo Library Selection (`PhotosPicker`)**  
  - *Dependencies:* `SCAF-05`  
  - *Acceptance Criteria:* Integrate SwiftUI `PhotosPicker` allowing secure out-of-process selection of packaging images (JPEG, PNG, WebP).  
  - *Verification Method:* Interactive test selects image from simulator/device photo library.  
  - *Status:* `[ ]` Not Started

- [ ] `CAM-04`: **On-Device Image Downsampling (`ImageCompressor`)**  
  - *Dependencies:* `SCAF-02`  
  - *Acceptance Criteria:* Implement `ImageCompressor` resizing high-resolution photos so file size is guaranteed under 8 MB (well below backend 10 MB limit) while preserving text legibility for PaddleOCR. Output valid JPEG with binary magic bytes `\xff\xd8\xff`.  
  - *Verification Method:* Unit test with 48MP sample image verifies output size < 8 MB and JPEG magic bytes.  
  - *Status:* `[ ]` Not Started

- [ ] `CAM-05`: **Photo Preview & Confirmation Sheet**  
  - *Dependencies:* `CAM-02`, `CAM-04`, `DSGN-05`  
  - *Acceptance Criteria:* Implement `PhotoPreviewSheet` displaying captured/selected photo with **"Retake"** button and **"Analyze Medicine"** primary CTA.  
  - *Verification Method:* SwiftUI preview tests photo review and button actions.  
  - *Status:* `[ ]` Not Started

- [ ] `CAM-06`: **Image-Only Analysis Submission**  
  - *Dependencies:* `CAM-05`, `NET-04`  
  - *Acceptance Criteria:* Submit image payload to `/api/analyze`; navigate to Processing view; handle success and navigate to Results view.  
  - *Verification Method:* Integration test verifies multipart request dispatch.  
  - *Status:* `[ ]` Not Started

---

## Section 10 — Phase 8: Symptoms & Voice Recording Pipeline

*Objective:* Implement the multiline symptom text composer, native audio recording, multiple clip management, and multimodal aggregation.

- [ ] `SYMP-01`: **Symptom Text Composer**  
  - *Dependencies:* `DSGN-07`  
  - *Acceptance Criteria:* Implement `SymptomEntryView` with multiline text editor, character counter (max 4,000 chars), and inline validation (reject empty submission).  
  - *Verification Method:* SwiftUI preview tests typing, character limit adherence, and placeholder behavior.  
  - *Status:* `[ ]` Not Started

- [ ] `SYMP-02`: **Audio Recording Service (`AVAudioRecorder`)**  
  - *Dependencies:* `SCAF-05`  
  - *Acceptance Criteria:* Implement `AudioRecorderService` recording 16-bit PCM WAV or AAC M4A audio. Verify file output starts with valid magic bytes (`RIFF....WAVE` or `....ftyp`).  
  - *Verification Method:* Unit test records dummy audio and inspects magic bytes.  
  - *Status:* `[ ]` Not Started

- [ ] `SYMP-03`: **Interactive Audio Recording Modal**  
  - *Dependencies:* `SYMP-02`, `DSGN-06`  
  - *Acceptance Criteria:* Implement `AudioRecordSheet` featuring live audio level meter / waveform, elapsed timer (`00:14`), stop button, and cancel button.  
  - *Verification Method:* Physical device test verifies live waveform animation during speech.  
  - *Status:* `[ ]` Not Started

- [ ] `SYMP-04`: **Audio Clip List & Playback**  
  - *Dependencies:* `SYMP-03`, `DSGN-06`  
  - *Acceptance Criteria:* Support up to 5 audio clips (`MAX_AUDIO_CLIPS_COUNT = 5`); display attached clips as chips with duration, playback toggle (`AVAudioPlayer`), and delete button.  
  - *Verification Method:* SwiftUI preview tests audio clip chip rendering, playback toggle, and deletion.  
  - *Status:* `[ ]` Not Started

- [ ] `SYMP-05`: **Multimodal Composer Aggregation**  
  - *Dependencies:* `SYMP-01`, `SYMP-04`, `CAM-05`  
  - *Acceptance Criteria:* Allow user to combine symptom text, recorded audio clips, and a medicine packaging image into a single analysis request.  
  - *Verification Method:* Unit test builds multipart request containing text, image, and multiple audio parts.  
  - *Status:* `[ ]` Not Started

---

## Section 11 — Phase 9: Processing State Machine & Clinical Results Presentation

*Objective:* Stream analysis requests, render the dynamic 6-step progress state machine, and display rich structured results with verified clinical safety styling.

- [ ] `RES-01`: **Processing State Machine UI**  
  - *Dependencies:* `DSGN-08`, `NET-04`  
  - *Acceptance Criteria:* Implement `ProcessingView` with dual-ring animated spinner, 2pt progress line, and dynamic stage messages cross-fading through the 6 backend stages:  
    1. *"Uploading data to secure server..."*  
    2. *"Transcribing voice audio with Faster-Whisper..."*  
    3. *"Extracting packaging label with PaddleOCR..."*  
    4. *"Matching symptoms against clinical FAISS databases..."*  
    5. *"Searching drug indications and contraindications..."*  
    6. *"Formulating clinical assessment with AI..."*  
  - *Verification Method:* SwiftUI preview verifies animation and step cycler timer.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-02`: **Results Screen Shell**  
  - *Dependencies:* `DSGN-01`, `DSGN-06`  
  - *Acceptance Criteria:* Implement `ResultDetailView` displaying completed analysis results parsed from the backend `card` object.  
  - *Verification Method:* SwiftUI preview renders full result view with mock card data.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-03`: **Verdict Hero Banner**  
  - *Dependencies:* `RES-02`, `DSGN-08`  
  - *Acceptance Criteria:* Implement verdict classification matching web frontend heuristic:  
    - **Danger (Red):** if `llm_output` contains *"not suitable"*, *"not appropriate"*, or *"mismatch"*.  
    - **Success (Green):** if `llm_output` contains *"suitable"*, *"appropriate"*, or *"match"*.  
    - **Warning (Amber):** fallback / caution.  
    Render badge, icon, and headline extracted from first markdown line.  
  - *Verification Method:* Unit test verifies verdict classification across danger, success, and warning sample strings.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-04`: **Clinical Explanation Section (Markdown)**  
  - *Dependencies:* `RES-02`, `DSGN-03`  
  - *Acceptance Criteria:* Render pharmacological rationale between verdict line and `### Suggested Alternatives` using native SwiftUI Markdown formatting (`LocalizedStringKey` or formatted `Text`).  
  - *Verification Method:* SwiftUI preview verifies bolding, lists, and paragraph formatting.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-05`: **Suggested Alternatives Section**  
  - *Dependencies:* `RES-02`, `DSGN-03`  
  - *Acceptance Criteria:* Extract and render pharmacotherapy alternatives under `### Suggested Alternatives` with bulleted lists and bold drug names.  
  - *Verification Method:* SwiftUI preview verifies alternatives rendering.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-06`: **Grounded Supporting Evidence (Collapsible RAG Accordions)**  
  - *Dependencies:* `RES-02`, `DSGN-06`  
  - *Acceptance Criteria:* Implement expandable accordion sections for:  
    - **Matched Diseases:** candidate disease name, similarity score, matched symptoms.  
    - **Matched Drugs:** brand name, generic name, indications.  
    - **Drug Dictionary:** brand-to-generic mapping and score.  
    Default to collapsed. Tapping triggers light selection haptic.  
  - *Verification Method:* Interactive testing verifies accordion expansion, collapse, and content presentation.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-07`: **Emergency Triage Warning Banner**  
  - *Dependencies:* `RES-02`, `DSGN-09`  
  - *Acceptance Criteria:* When `meta.guardrail.is_emergency == true` or critical symptoms are flagged, render prominent red emergency banner: *"Call 112 (India), 911 (US), or local emergency services immediately."*  
  - *Verification Method:* SwiftUI preview verifies emergency triage banner appearance.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-08`: **OCR Unreadable Image Fallback Presentation**  
  - *Dependencies:* `RES-02`, `DSGN-09`  
  - *Acceptance Criteria:* When `meta.ocr_status == "FAILED"` or image is unreadable, render clear instructional box guiding the user to enter text or provide a clearer photo.  
  - *Verification Method:* SwiftUI preview verifies OCR fallback rendering.  
  - *Status:* `[ ]` Not Started

- [ ] `RES-09`: **Mandatory Medical Disclaimer Banner**  
  - *Dependencies:* `RES-02`, `DSGN-09`  
  - *Acceptance Criteria:* Render persistent boxed notice: *"MediScanAI provides automated informational assistance and is not a qualified healthcare professional. Always consult a licensed physician for medical decisions."*  
  - *Verification Method:* Visual inspection verifies disclaimer presence on every result view.  
  - *Status:* `[ ]` Not Started

---

## Section 12 — Phase 10: Analysis History, Profile & Settings

*Objective:* Implement the paginated history list, historical record detail rehydration, record deletion, account details, and server settings.

- [ ] `HIST-01`: **History List View**  
  - *Dependencies:* `NAV-01`, `NET-03`  
  - *Acceptance Criteria:* Implement `HistoryListView` calling `GET /api/analyses?limit=20&offset=0`. Display items in chronological grouped sections with modality icon badge (`multimodal`, `image`, `text`, `audio`), relative timestamp, and 2-line verdict snippet.  
  - *Verification Method:* SwiftUI preview verifies populated history list.  
  - *Status:* `[ ]` Not Started

- [ ] `HIST-02`: **Pagination & Pull-to-Refresh**  
  - *Dependencies:* `HIST-01`  
  - *Acceptance Criteria:* Support `.refreshable` pull-to-refresh; automatically fetch next page when user scrolls to bottom of list until `total` records are loaded.  
  - *Verification Method:* Unit test verifies pagination offset math and list concatenation.  
  - *Status:* `[ ]` Not Started

- [ ] `HIST-03`: **Historical Record Detail Rehydration**  
  - *Dependencies:* `HIST-01`, `RES-02`  
  - *Acceptance Criteria:* Tapping a history item calls `GET /api/analyses/{id}`, rehydrates the full `ResultDetailView`, and pushes onto navigation stack.  
  - *Verification Method:* Interactive test loads and displays a historical analysis card.  
  - *Status:* `[ ]` Not Started

- [ ] `HIST-04`: **Analysis Record Deletion**  
  - *Dependencies:* `HIST-01`, `NET-03`  
  - *Acceptance Criteria:* Swipe left on history item reveals red **"Delete"** action. Tapping triggers confirmation dialog; on confirmation, dispatches `DELETE /api/analyses/{id}`, animates row removal, and provides haptic feedback.  
  - *Verification Method:* Interactive test deletes item and verifies list update.  
  - *Status:* `[ ]` Not Started

- [ ] `HIST-05`: **History Empty & Error States**  
  - *Dependencies:* `HIST-01`, `DSGN-06`  
  - *Acceptance Criteria:* Display clean empty state (*"No Past Analyses. Start by scanning medicine or logging symptoms."*) and retryable error state on network failure.  
  - *Verification Method:* SwiftUI preview tests empty and error history states.  
  - *Status:* `[ ]` Not Started

- [ ] `PROF-01`: **User Profile View**  
  - *Dependencies:* `NAV-01`, `AUTH-02`  
  - *Acceptance Criteria:* Implement `ProfileView` displaying user full name, email, member since date, server connection status, and sign-out trigger.  
  - *Verification Method:* SwiftUI preview verifies user profile layout.  
  - *Status:* `[ ]` Not Started

- [ ] `PROF-02`: **Legal Disclaimers & App Info**  
  - *Dependencies:* `PROF-01`, `DSGN-06`  
  - *Acceptance Criteria:* Grouped section displaying app version, build number, local privacy policy link, and full medical legal disclaimers.  
  - *Verification Method:* Visual inspection of Profile disclosures.  
  - *Status:* `[ ]` Not Started

- [ ] `PROF-03`: **Sign-Out Workflow**  
  - *Dependencies:* `PROF-01`, `AUTH-06`  
  - *Acceptance Criteria:* Tapping "Sign Out" presents confirmation alert. On confirm, wipes Keychain token, resets `AuthManager` to `.unauthenticated`, and routes navigation to login screen.  
  - *Verification Method:* Unit test and interactive test verify complete sign-out flow.  
  - *Status:* `[ ]` Not Started

---

## Section 13 — Phase 11: Quality Assurance, Regression Gates & Release Readiness

*Objective:* Execute unit, integration, UI, physical device, and non-regression test suites to certify production readiness.

- [ ] `QA-01`: **iOS Unit Test Suite Execution**  
  - *Dependencies:* `NET-01` through `AUTH-06`  
  - *Acceptance Criteria:* Execute unit tests covering `APIClient`, `MultipartFormDataBuilder`, `KeychainStorage`, `AuthManager`, `ImageCompressor`, and verdict classification. 100% pass rate.  
  - *Verification Method:* `xcodebuild test -project ios/MediScanAI.xcodeproj -scheme MediScanAI -destination "platform=iOS Simulator,name=iPhone 15"` exits code 0.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-02`: **iOS UI Integration Tests (XCUITest)**  
  - *Dependencies:* `QA-01`, `NAV-01`  
  - *Acceptance Criteria:* Automated UI tests verifying: app launch, sign-in, tab switching, symptom entry, results navigation, history inspection, and sign-out.  
  - *Verification Method:* XCUITest suite passes cleanly on simulator.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-03`: **Physical iPhone Local Wi-Fi Validation**  
  - *Dependencies:* `QA-01`, `WIFI-02`  
  - *Acceptance Criteria:* Deploy app to physical iPhone connected to same Wi-Fi as host Mac. Successfully execute end-to-end:  
    1. Connect to backend at `http://192.168.0.155:8000`.  
    2. Register or log in.  
    3. Capture real packaging label photo via camera and run analysis.  
    4. Record voice symptoms via microphone and run multimodal analysis.  
    5. Inspect structured results and collapsible evidence.  
    6. Verify past analyses in history and delete a record.  
  - *Verification Method:* Physical device manual execution logs and screenshot capture.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-04`: **Rate Limit (429) & Concurrency (503) Handling Verification**  
  - *Dependencies:* `NET-06`, `RES-01`  
  - *Acceptance Criteria:* Verify that when backend returns HTTP 429 or 503, the iOS app displays the appropriate `Retry-After` countdown notice without crashing or spamming requests.  
  - *Verification Method:* Mocked response tests and simulated concurrent analysis requests.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-05`: **Oversized Media Boundary Rejection**  
  - *Dependencies:* `CAM-04`, `SYMP-04`  
  - *Acceptance Criteria:* Test uploading files exceeding limits (10MB image, 25MB audio, >5 audio clips, >4000 char text); verify client pre-flight checks and backend 400 responses are handled gracefully.  
  - *Verification Method:* Automated unit/integration tests with oversized payloads.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-06`: **Accessibility, Dynamic Type & VoiceOver Verification**  
  - *Dependencies:* `DSGN-03`  
  - *Acceptance Criteria:* Verify all screens support XXL Dynamic Type without text truncation; verify all interactive elements possess meaningful `.accessibilityLabel` modifiers for VoiceOver.  
  - *Verification Method:* Xcode Accessibility Inspector audit.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-07`: **Memory Leak & Profile Inspection**  
  - *Dependencies:* `QA-03`  
  - *Acceptance Criteria:* Profile the app using Xcode Instruments (Leaks, Allocations) during heavy photo captures and audio recordings; confirm zero memory leaks and stable memory footprint (< 100 MB).  
  - *Verification Method:* Xcode Instruments memory trace report.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-08`: **Website Production Build Non-Regression Gate**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* `cd frontend && npm run build` must compile cleanly with exit code 0.  
  - *Verification Method:* Execute command; verify build output.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-09`: **Website Linter Non-Regression Gate**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* `cd frontend && npm run lint` must report 0 errors and no more than 11 warnings.  
  - *Verification Method:* Execute command; verify Oxlint output.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-10`: **Backend Deterministic Test Non-Regression Gate**  
  - *Dependencies:* None  
  - *Acceptance Criteria:* `pytest tests/api tests/database tests/test_e2e_smoke.py -v` must execute and pass without failures against a running database instance.  
  - *Verification Method:* Pytest run report.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-11`: **Git Diff Scope & Cleanliness Verification**  
  - *Dependencies:* All previous tasks  
  - *Acceptance Criteria:* `git diff --check` passes with zero whitespace or formatting errors. `git status --short` confirms modifications are strictly confined to `ios/` and `mediscanai-app-spec/`.  
  - *Verification Method:* Git inspection commands pass cleanly.  
  - *Status:* `[ ]` Not Started

- [ ] `QA-12`: **Final Release Milestone Sign-Off**  
  - *Dependencies:* `QA-01` through `QA-11`  
  - *Acceptance Criteria:* Formal sign-off by Technical Project Manager and Senior iOS Architect certifying complete Phase 1–11 execution.  
  - *Verification Method:* Sign-off document generated in `mediscanai-app-spec/`.  
  - *Status:* `[ ]` Not Started

---

## Section 14 — Future Enhancements: Remote Connectivity (Explicitly Deferred)

*Note: These tasks belong to a future phase and are NOT part of the initial local-network release. They are documented here to guarantee forward architectural compatibility.*

- [ ] `REM-01`: **Tailscale Mesh VPN Integration (DEFERRED)**  
  - *Scope:* Connect iPhone and MacBook over Tailscale VPN; route API traffic via MacBook's MagicDNS hostname (e.g., `https://macbook-air.tailnet.ts.net`).  
  - *Status:* `[ ]` Not Started (Deferred)

- [ ] `REM-02`: **Automatic TLS / HTTPS Certificate Handling (DEFERRED)**  
  - *Scope:* Configure Tailscale HTTPS certificates or Caddy automatic TLS termination for encrypted remote transit.  
  - *Status:* `[ ]` Not Started (Deferred)

- [ ] `REM-03`: **Remote Server Profile Manager (DEFERRED)**  
  - *Scope:* Allow user to toggle between "Local Wi-Fi" and "Remote Tailscale" server connection profiles in settings.  
  - *Status:* `[ ]` Not Started (Deferred)

- [ ] `REM-04`: **Cellular Data Optimization (DEFERRED)**  
  - *Scope:* Add low-bandwidth mode to further compress packaging photos when operating over mobile cellular data.  
  - *Status:* `[ ]` Not Started (Deferred)

- [ ] `REM-05`: **Remote Access Security Review (DEFERRED)**  
  - *Scope:* Re-evaluate device access controls and rate limiting before public/mesh exposure.  
  - *Status:* `[ ]` Not Started (Deferred)

