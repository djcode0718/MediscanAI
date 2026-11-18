# MediScanAI — Native iOS Architecture & Technical Design Recommendation

**Document:** `mediscanai-app-spec/05_IOS_ARCHITECTURE_RECOMMENDATION.md`  
**Status:** Recommended Technical Architecture  
**Target Platform:** iOS 17.0+ (Swift 5.10 / 6.0, SwiftUI)  
**Hardware Target:** iPhone (with iPad support if requested)  
**Host Connectivity:** Local Wi-Fi to MacBook Air M4 Backend (Tailscale-ready)  
**Constraint:** 100% additive isolation inside `ios/`; zero changes to web frontend.

---

## 1. Architectural Philosophy & Technology Choices

The native iOS client for MediScanAI must deliver a **first-class Apple platform experience**: responsive, memory-efficient, visually calm, and strictly respectful of iOS human interface conventions.

### Core Technology Decisions
1. **SwiftUI + Swift Concurrency:** Use 100% declarative SwiftUI with modern `async`/`await`, `@Observable` (Observation framework in iOS 17), and structured actors. Avoid legacy Combine or UIKit storyboards.
2. **Native URLSession Client:** Avoid bloated third-party dependencies (e.g., Alamofire). A lightweight, typed `APIClient` protocol built over `URLSession` handles REST JSON and streaming multipart uploads with zero third-party baggage.
3. **Apple Keychain for Tokens:** Store JWT session tokens in the hardware-backed Secure Enclave / Keychain Services API (`kSecClassGenericPassword`). Never write auth tokens to `UserDefaults` or plaintext files.
4. **Hardware AVFoundation Pipelines:**
   - **Camera:** Custom lightweight `AVCaptureSession` viewfinder with pinch-to-zoom, tap-to-focus, and optical stabilization.
   - **Photo Library:** Modern `PhotosPicker` (from `PhotosUI`) for secure out-of-process image selection without requiring full library read permissions.
   - **Microphone:** Dedicated `AVAudioRecorder` configured for 16-bit PCM WAV or high-efficiency AAC M4A.
5. **Configurable Local Base URL:** Configurable base URL stored in `UserDefaults` (defaulting to the local host address e.g., `http://192.168.1.100:8000`) with an inline connection verifier that hits `GET /api/health`.

---

## 2. Recommended Directory & Module Layout

The entire iOS codebase will reside cleanly in the `ios/` root directory:

```
ios/
├── MediScanAI.xcodeproj / MediScanAI.xcworkspace
├── MediScanAI/
│   ├── App/
│   │   ├── MediScanAIApp.swift            # SwiftUI @main entry point
│   │   ├── AppCoordinator.swift           # Root navigation & session routing
│   │   └── AppEnvironment.swift           # Central dependency container
│   ├── Core/
│   │   ├── Networking/
│   │   │   ├── APIEndpoint.swift          # Type-safe route builder
│   │   │   ├── APIClient.swift            # URLSession wrapper with async/await
│   │   │   ├── MultipartBuilder.swift     # Streaming multipart/form-data encoder
│   │   │   ├── NetworkError.swift         # Structured error mapping (401, 429, 503)
│   │   │   └── ServerConfig.swift         # Base URL management & health probing
│   │   ├── Authentication/
│   │   │   ├── AuthManager.swift          # Session state coordinator
│   │   │   ├── KeychainStorage.swift      # Secure Enclave token wrapper
│   │   │   └── UserSession.swift          # User model & active token representation
│   │   ├── DesignSystem/
│   │   │   ├── Colors.swift               # Monochromatic tokens & OLED palette
│   │   │   ├── Typography.swift           # Dynamic Type hierarchy
│   │   │   ├── Spacing.swift              # 4pt grid tokens & safe-area metrics
│   │   │   └── Components/
│   │   │       ├── PrimaryButton.swift    # High-contrast action CTA
│   │   │       ├── SurfaceCard.swift      # Tonal surface container
│   │   │       ├── VerdictBadge.swift     # Danger / Success / Caution pill
│   │   │       ├── StatusIndicator.swift  # Loading ring & pulse animation
│   │   │       └── NoticeBanner.swift     # Medical disclaimer and error banners
│   │   ├── Media/
│   │   │   ├── CameraService.swift        # AVCaptureSession camera controller
│   │   │   ├── AudioRecorderService.swift # AVAudioRecorder controller
│   │   │   └── ImageCompressor.swift      # Safe JPEG downscaling (max 10 MB)
│   │   └── Utilities/
│   │       ├── HapticFeedback.swift       # Sensory haptic patterns
│   │       └── DateFormatter+Format.swift # ISO8601 formatting utilities
│   ├── Features/
│   │   ├── Auth/
│   │   │   ├── LoginView.swift            # Email/Password sign-in
│   │   │   ├── RegisterView.swift         # Full name, email, password sign-up
│   │   │   └── AuthViewModel.swift        # Auth state machine
│   │   ├── Home/
│   │   │   ├── HomeView.swift             # Main dashboard & quick actions
│   │   │   └── HomeViewModel.swift        # Recent activity rehydration
│   │   ├── Scan/
│   │   │   ├── CameraScanView.swift       # Fullscreen packaging viewfinder
│   │   │   ├── PhotoPreviewSheet.swift    # Image review, crop & retake
│   │   │   └── ScanViewModel.swift        # Image pipeline state
│   │   ├── Symptoms/
│   │   │   ├── SymptomEntryView.swift     # Spacious text entry + voice dock
│   │   │   ├── AudioRecordSheet.swift     # Interactive audio waveform & timer
│   │   │   └── SymptomsViewModel.swift    # Symptom aggregation state
│   │   ├── Analysis/
│   │   │   ├── ProcessingView.swift       # Staged progress indicator
│   │   │   ├── ResultDetailView.swift     # Structured verdict, explanation & RAG
│   │   │   └── AnalysisViewModel.swift    # Execution state machine
│   │   ├── History/
│   │   │   ├── HistoryListView.swift      # Paginated history list
│   │   │   ├── HistoryDetailView.swift    # Rehydrated analysis inspection
│   │   │   └── HistoryViewModel.swift     # Cache & deletion logic
│   │   └── Profile/
│   │       ├── ProfileView.swift          # Account info, server config, sign out
│   │       └── ServerConfigSheet.swift    # Wi-Fi IP address configuration
│   └── Resources/
│       ├── Assets.xcassets                # App icon, splash brand assets
│       ├── Info.plist                     # Camera/Microphone privacy justifications
│       └── PrivacyInfo.xcprivacy          # Apple Privacy Manifest
├── MediScanAITests/                       # Unit tests (Networking, Models, Keychain)
└── MediScanAIUITests/                     # UI integration tests
```

---

## 3. Core Architectural Subsystems

### 3.1 Networking Layer & Multipart Streaming
To handle multimodal submissions without loading large assets repeatedly into memory, the `MultipartBuilder` creates a streaming `URLRequest`:

```swift
// Example architectural interface
protocol APIClientProtocol: Sendable {
    func request<T: Decodable>(_ endpoint: APIEndpoint) async throws -> T
    func uploadMultipart<T: Decodable>(
        endpoint: APIEndpoint,
        text: String?,
        image: Data?,
        audioClips: [Data]
    ) async throws -> T
}
```

**HTTP Error Mapping:**
- `401 Unauthorized`: Broadcasts a session termination signal to `AuthManager`, immediately wiping the Keychain and presenting the login sheet.
- `429 Too Many Requests`: Decodes the `Retry-After` header and presents a localized countdown timer.
- `503 Service Unavailable`: Identifies slot capacity saturation vs. backend model warming, notifying the user calmly without crashing.

### 3.2 Keychain Authentication & Session State
Token security follows the Apple Keychain Services standard:

```swift
final class KeychainStorage: Sendable {
    private let service = "com.mediscanai.ios"
    private let tokenKey = "auth_token"

    func saveToken(_ token: String) throws { ... }
    func getToken() -> String? { ... }
    func deleteToken() throws { ... }
}
```

The `AuthManager` is marked `@Observable` and acts as the single source of truth for user authentication state throughout the app hierarchy:
- `.unauthenticated`: Renders `LandingAuthView`.
- `.authenticating`: Disables buttons and presents inline indicators.
- `.authenticated(UserSession)`: Unlocks the primary navigation container.

### 3.3 Local Wi-Fi Networking & ATS Exception Design

In the initial release, the backend operates on the developer's MacBook Air M4 on the local home/office Wi-Fi (e.g. `192.168.1.100:8000`).

**App Transport Security (ATS) Rules:**
- iOS strictly enforces HTTPS by default.
- To connect over local plain HTTP without compromising overall app security, ATS exceptions must be **narrowly scoped** in `Info.plist`:
  ```xml
  <key>NSAppTransportSecurity</key>
  <dict>
      <key>NSAllowsLocalNetworking</key>
      <true/>
  </dict>
  ```
- `NSAllowsLocalNetworking: true` is an officially sanctioned Apple key that permits direct connections to local IPv4/IPv6 subnets and `.local` mDNS domains while keeping standard external internet traffic locked to HTTPS.
- Global `NSAllowsArbitraryLoads` is **strictly forbidden**.

**Connection Verifier Feature:**
- In the `Profile` / `Server Settings` sheet, the user can input the MacBook's local LAN IP.
- A "Test Connection" button dispatches an unauthenticated ping to `GET /api/health`.
- Visual badge updates immediately:
  - 🟢 Connected: *MediScanAI backend active (v1.0.0, development)*
  - 🔴 Unreachable: *Ensure Mac backend is running and iPhone is on the same Wi-Fi network.*

### 3.4 Future Private Remote Connectivity (Tailscale Ready)
The networking layer uses a centralized `ServerConfig.baseURL` provider. When Tailscale connectivity is introduced:
- The base URL is simply switched from `http://192.168.1.X:8000` to the MacBook's Tailscale MagicDNS address (e.g., `https://macbook-air.tailnet.ts.net`).
- Zero changes are required to the ViewModels, Views, or API contract.

---

## 4. UI State Machine Architecture

Every interactive screen adopts an explicit, non-optional state machine to prevent inconsistent UI states:

```swift
enum ViewState<T> {
    case idle
    case loading(String)   // Active stage description (e.g., "Transcribing audio...")
    case success(T)        // Completed payload
    case empty             // No records found
    case error(AppError)   // Actionable error with recovery trigger
}
```

### Swift Concurrency & Task Cancellation
- Network requests are bound to view lifecycles using `.task { ... }`.
- If a user navigates away or cancels a submission, the Swift runtime cooperatively cancels the underlying `URLSessionDataTask`, conserving device battery and avoiding unneeded processing.

---

## 5. Medical Safety & Privacy Controls

1. **Explicit Permission Pre-Flights:** Before requesting camera or microphone access, MediScanAI will display an explanatory modal explaining *why* the sensor is required (e.g., *"MediScanAI uses your camera exclusively to capture packaging labels for text recognition"*).
2. **Mandatory Disclaimers:** Every analysis screen and detail card renders the persistent legal medical disclaimer:
   > *"MediScanAI provides automated informational assistance and is not a qualified healthcare professional. Always consult a licensed physician for medical decisions."*
3. **No Third-Party Analytics:** Zero tracking SDKs, Firebase Analytics, Facebook SDK, or third-party telemetry libraries.

