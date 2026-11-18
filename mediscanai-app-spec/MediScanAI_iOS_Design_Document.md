# MediScanAI iOS — UI/UX Design Document & Design System

**Document Version:** 1.0 (Audited & Reconciled Design Specification)  
**Status:** Approved for Implementation  
**Platform:** Native iOS 17.0+ (SwiftUI)  
**Character:** Premium · Minimal · Monochromatic · Calm · Precise  
**Visual Foundation:** True-Black OLED (`#000000`) with Tonal Elevation  
**Accessibility:** Full Dynamic Type support, WCAG AAA contrast for text, and native VoiceOver labels

---

## 1. Design Vision & Philosophy

MediScanAI on iPhone is designed as a **quiet, authoritative, and clinical health copilot**. It decisively avoids the clichés of consumer AI apps:
- ❌ No generic glowing neon gradients or glassmorphism bubbles.
- ❌ No theatrical chatbot avatars or conversational fluff.
- ❌ No cluttered dashboards crammed with vanity health scores.

Instead, the interface embraces **calm restraint**: high-contrast typography, deep true-black backgrounds that conserve OLED battery life, subtle tonal surface elevation, and purposeful semantic color used exclusively to communicate clinical verdicts and warnings.

---

## 2. Color System & Design Tokens

### 2.1 Monochromatic Surface Tokens
Depth is created through tonal layering rather than heavy drop shadows or thick outlines:

| Token Name | Hex Value | Usage / Semantic Role |
| :--- | :--- | :--- |
| `background` | `#000000` | Canvas base layer for all fullscreen views (true OLED black) |
| `surfacePrimary` | `#0A0A0A` | Primary container sections and list row backgrounds |
| `surfaceSecondary` | `#141414` | Grouped cards, input containers, and unselected controls |
| `surfaceTertiary` | `#1E1E1E` | Hovered or active inputs, chips, and selected states |
| `surfaceElevated` | `#262626` | Modals, bottom sheets, and floating action sheets |
| `borderSubtle` | `#2A2A2A` | Restrained 1px dividers and card borders |
| `borderFocus` | `#404040` | Focused text inputs and active viewfinder reticles |

### 2.2 Text & Iconography Tokens
| Token Name | Hex Value | Typography Role | Contrast Ratio |
| :--- | :--- | :--- | :--- |
| `textPrimary` | `#FFFFFF` | Headlines, primary labels, and user inputs | 21:1 (AAA) |
| `textSecondary` | `#A1A1A1` | Explanatory paragraphs, section captions, and subheadings | 9.8:1 (AAA) |
| `textTertiary` | `#707070` | Timestamps, metadata labels, and input placeholders | 4.8:1 (AA) |
| `iconPrimary` | `#F5F5F5` | Action icons, navigation triggers, and back buttons | High |
| `iconSecondary` | `#929292` | Auxiliary icons, chevron disclosures, and trailing indicators | Medium |
| `accentNeutral` | `#FFFFFF` | Primary call-to-action button fill (inverted text `#000000`) | Maximum |

### 2.3 Semantic Clinical Accent Tokens
Semantic colors are strictly reserved for communicating diagnostic status and safety information. They are never used as decorative brand accents:

| Status Role | Base Hex | Subtle Fill Hex | Border Hex | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Danger / Not Suitable** | `#F43F5E` | `#2D0A14` | `#5C1D2C` | Dangerous interactions, unsuited medicines, acute emergencies |
| **Success / Suitable** | `#10B981` | `#06281E` | `#0D5C45` | Verified clinical suitability, matched indications, active connection |
| **Warning / Caution** | `#F59E0B` | `#2E1E05` | `#5C4010` | Inconclusive OCR, partial contraindications, rate limit countdowns |

---

## 3. Typography Hierarchy

The type system is built on **San Francisco Pro** with proportional leading and system Dynamic Type scaling:

| Text Style | SF Weight | Point Size | Leading | Tracking | Native SwiftUI Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Large Title** | Bold | 34 pt | 41 pt | +0.37 | Screen titles (Home, History) |
| **Title 1** | Semibold | 28 pt | 34 pt | +0.36 | Modal sheet headers |
| **Title 2** | Semibold | 22 pt | 28 pt | +0.35 | Verdict headline and section cards |
| **Title 3** | Medium | 20 pt | 25 pt | +0.38 | Sub-section headings |
| **Headline** | Semibold | 17 pt | 22 pt | -0.41 | Card headers, list item titles |
| **Body** | Regular | 17 pt | 22 pt | -0.41 | Primary clinical explanation text |
| **Callout** | Regular | 16 pt | 21 pt | -0.32 | High-priority warnings, notes |
| **Subheadline** | Regular | 15 pt | 20 pt | -0.24 | Secondary metadata, dates |
| **Footnote** | Regular | 13 pt | 18 pt | -0.08 | Legal disclaimers, timing badges |
| **Caption 1** | Medium | 12 pt | 16 pt | 0.00 | Modality pills, tags, status |

*Rule:* Tabular numerals (`.monospacedDigit()`) must be used for durations, timestamps, and confidence percentages to prevent layout jitter.

---

## 4. Spacing Scale & Corner Radii

### 4.1 Spacing Scale (4pt Grid)
- `4 pt`: Micro padding (inside badges and pills).
- `8 pt`: Compact gap (between icon and label, chip spacing).
- `12 pt`: Small gap (between form fields, list item vertical padding).
- `16 pt`: Standard gap (card interior padding, standard gutters).
- `20 pt`: Large gap (screen horizontal margins on standard iPhones).
- `24 pt`: Screen horizontal margins on Plus/Pro Max devices; section separators.
- `32 pt`: Major section rhythm.
- `48 pt`: Screen header and footer clearances.

### 4.2 Corner Radii Scale
- `8 pt`: Small chips, badges, and tag pills.
- `12 pt`: Compact buttons, text fields, and icon containers.
- `16 pt`: Standard surface cards and interactive list rows.
- `24 pt`: Modal bottom sheets and full-bleed action containers.
- `999 pt`: Circular icon buttons and pill indicators.

---

## 5. Screen Direction & Flow Specifications

### 5.1 Authentication (Sign-In & Sign-Up)
- **Canvas:** `#000000` with subtle monochrome heart/cross brand mark.
- **Entry Points:** Clean toggle between Sign In and Sign Up.
- **Inputs:** High-contrast bordered inputs with clear placeholder and system autocomplete tags (`.emailAddress`, `.password`).
- **Feedback:** Discrete red inline warning banner if credentials are rejected.

### 5.2 Home Dashboard
- **Header:** Clean wordmark + connection status badge (`🟢 Local Wi-Fi`).
- **Primary Hero Action:** Large card **"Scan Medicine"** with camera icon.
- **Secondary Actions:** Side-by-side cards: **"Enter Symptoms"** and **"Record Voice"**.
- **Recent Activity:** Compact view of the latest 3 analyses with quick rehydration trigger.

### 5.3 Medicine Packaging Scan (Camera Viewfinder)
- **Live Feed:** Hardware `AVCaptureSession` feed with corner reticles.
- **Shutter Control:** Floating white capture button with tactile haptic feedback.
- **Secondary Action:** Native photo picker button to select from gallery.
- **Preview Confirmation:** Instant review sheet with **"Retake"** or **"Analyze"** triggers.

### 5.4 Multimodal Composer (Symptom Text + Voice Audio)
- **Text Area:** Large multiline editor supporting Dynamic Type.
- **Attachment Bar:** Floating chips for attached packaging photos or recorded voice clips.
- **Audio Recorder Modal:** Live waveform visualizer with active duration timer and stop/cancel controls.
- **Submit Action:** Full-width high-contrast white button **"Run Analysis"**.

### 5.5 Staged Processing State
- **Spinner:** Dual-concentric white ring spinner with subtle pulse.
- **Dynamic Copy:** Cross-fading backend stage messages:
  1. *"Uploading multimodal data to secure server..."*
  2. *"Transcribing voice audio with Faster-Whisper..."*
  3. *"Extracting packaging label with PaddleOCR..."*
  4. *"Matching symptoms against clinical FAISS databases..."*
  5. *"Retrieving drug indications and contraindications..."*
  6. *"Formulating clinical assessment with AI..."*
- **Progress Line:** Subtle 2pt indicator bar tracking stage progression.

### 5.6 Clinical Results View
- **Verdict Hero Banner:** High-visibility status container:
  - Danger (Red tone): *"Not Suitable for Stated Symptoms"*
  - Success (Green tone): *"Clinically Suitable / Expected Match"*
  - Warning (Amber tone): *"Caution / Inconclusive Evidence"*
- **Clinical Explanation:** Markdown body explaining pharmacological mechanisms.
- **Suggested Alternatives:** Bulleted alternative medications and active molecules.
- **Collapsible RAG Evidence:** Accordion views for matched diseases, drug labeling, and drug dictionary candidates.
- **Medical Disclaimer:** Persistent legal disclaimer banner with emergency contact notice (112 / 911).

### 5.7 History List & Detail Viewer
- **List Rows:** Grouped cards showing modality badge, creation date/time, and 2-line verdict snippet.
- **Swipe Actions:** Swipe left reveals red **"Delete"** action with haptic confirmation.
- **Detail Viewer:** Tapping rehydrates the full historical result card.

### 5.8 Profile & Local Server Settings
- **User Identity:** Display name, email address, registration timestamp.
- **Server Connection:** Editable LAN IP address (`http://192.168.1.X:8000`) with **"Test Connection"** ping.
- **Legal & Safety:** Links to data policy, educational notices, and open-source licenses.
- **Sign Out:** High-contrast red row with confirmation sheet.

---

## 6. Reusable Component Library Specification

1. `PrimaryButton`: Full-width or inline white button (`#FFFFFF`) with black text (`#000000`), 12pt radius, pressed state downscale to `0.98`.
2. `SecondaryButton`: Dark surface (`#1E1E1E`) with white text and subtle border (`#2A2A2A`).
3. `SurfaceCard`: Tonal background (`#141414`), 16pt radius, subtle 1px border (`#2A2A2A`), 16pt interior padding.
4. `VerdictBadge`: Status capsule with status icon, status text, and tinted fill (Red/Green/Amber).
5. `NoticeBanner`: Full-bleed or bordered alert box with medical disclaimer or error messaging.
6. `StatusIndicator`: Animated dual-ring spinner with progress stage text.
7. `MediaChip`: Compact 8pt radius chip displaying media type icon, title, duration/size, and remove button.

---

## 7. Resolution of Design Decisions

| Decision Area | Final Resolved Specification |
| :--- | :--- |
| **Navigation Structure** | 4-Tab Native Bar: `Home`, `Scan`, `History`, `Profile`. |
| **Onboarding Experience** | Direct entry to Sign In / Sign Up; no decorative or multi-step tutorial carousels. |
| **Color Contrast** | Monochromatic palette exceeds WCAG AAA (21:1 for primary text, 9.8:1 for secondary text). |
| **Scan Action Priority** | Dedicated tab + hero card on Home tab. |
| **Result Structure** | 4 explicit sections: Verdict Hero, Clinical Explanation, Suggested Alternatives, Collapsible Evidence. |
| **Voice Audio Support** | Included in first release (AVAudioRecorder -> `/api/analyze`). |
| **Supported OS Target** | iOS 17.0+ (utilizing `@Observable`, `PhotosPicker`, and modern Swift concurrency). |
