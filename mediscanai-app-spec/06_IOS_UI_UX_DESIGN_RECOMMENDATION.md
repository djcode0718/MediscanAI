# MediScanAI — iOS UI/UX Design System & Screen Specifications

**Document:** `mediscanai-app-spec/06_IOS_UI_UX_DESIGN_RECOMMENDATION.md`  
**Status:** Recommended UI/UX Design Specification  
**Design Character:** Premium · Minimalist · Monochromatic · Calm · Precise  
**Visual Foundation:** True-Black OLED (`#000000`) with Tonal Surface Layering  
**Typography:** Apple San Francisco Pro (`SF Pro`) with full Dynamic Type support

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

## 5. Detailed Screen Specifications

### 5.1 Authentication Screens (Login & Register)
- **Visuals:** Pure `#000000` background. Subtle white brand mark at top center.
- **Form Controls:** Clean input fields with `#141414` background, `#2A2A2A` border, and active focus ring `#404040`.
- **Keyboard Behavior:** Native keyboard dismiss on tap-outside; submit button shifts gracefully above the keyboard avoiding occlusion.
- **Validation:** Clear, non-jarring inline error text (`#F43F5E`) when credentials fail.

### 5.2 Home Dashboard Screen
- **Header:** Discreet MediScanAI wordmark + active connection status pill (`🟢 Local Wi-Fi`).
- **Primary Hero Action:** Large elevated card: **"Scan Medicine"** with camera icon, subtitle *"Inspect packaging, extract active molecules & verify safety"*.
- **Secondary Actions:** Dual horizontal grid cards:
  - **"Enter Symptoms"** (text entry).
  - **"Voice Recording"** (microphone icon).
- **Recent Analyses Section:** Compact list showing the 3 most recent analyses with modality badge, verdict headline snippet, and timestamp.
- **Floating Action Bar / Navigation:** Restrained bottom tab bar: `Home`, `Scan`, `History`, `Profile`.

### 5.3 Medicine Packaging Scan Screen
- **Viewfinder:** Fullscreen live camera feed powered by `AVCaptureSession`.
- **Framing Guide:** Minimalist corner reticles framing the target packaging label.
- **Controls Overlay:**
  - Top bar: Close button (left), Flashlight toggle (right).
  - Bottom control deck:
    - Photo Library picker button (left).
    - Large shutter button (center, white circle with inner ring).
    - Mode toggle (right).
- **Preview Sheet:** After capture, an instant preview displays the photo with actions:
  - **"Retake"** (secondary outline button).
  - **"Analyze Medicine"** (primary white CTA).

### 5.4 Symptom Entry & Multimodal Composer Screen
- **Input Surface:** Spacious multiline text editor with placeholder *"Describe your symptoms, dosage questions, or condition..."*.
- **Attachment Strip:** Attached media chips appear above the keyboard:
  - Image thumbnail chip (with tap-to-remove).
  - Voice recording chip (with playback duration and tap-to-remove).
- **Voice Recording Sheet:** Dedicated bottom sheet with live waveform visualizer, recording duration counter (`00:14`), and large stop/confirm trigger.
- **Submit Button:** Full-width primary button **"Run Analysis"** anchored above keyboard or bottom safe area.

### 5.5 Processing & Inference Screen
- **Visuals:** Calm, focused state while awaiting backend response.
- **Visualizer:** Dual-concentric white ring spinner with subtle pulse animation.
- **Staged Message Indicator:** Dynamic text smoothly cross-fading through the backend's actual execution stages:
  1. *"Uploading multimodal data to secure server..."*
  2. *"Transcribing voice audio with Faster-Whisper..."*
  3. *"Extracting packaging label with PaddleOCR..."*
  4. *"Matching symptoms against clinical FAISS databases..."*
  5. *"Retrieving drug indications and contraindications..."*
  6. *"Formulating clinical assessment with AI..."*
- **Progress Bar:** Subtle 2pt line showing stage progression.

### 5.6 Clinical Results Screen
- **Verdict Hero Banner:** High-visibility status container styling:
  - Danger (Red tone): *"Not Suitable for Stated Symptoms"*
  - Success (Green tone): *"Clinically Suitable / Expected Match"*
  - Warning (Amber tone): *"Caution / Inconclusive Evidence"*
- **Section 1 — Clinical Explanation:** Markdown-formatted body text detailing pharmacological rationale and interaction mechanisms.
- **Section 2 — Suggested Alternatives:** Bulleted pharmacotherapy alternatives (e.g., active molecule names, indications).
- **Section 3 — Grounded Supporting Evidence:** Collapsible accordions showing raw RAG retrieval passages:
  - Matched Diseases (similarity score + clinical symptoms).
  - Matched Drugs (indications, active ingredients).
  - Drug Dictionary (brand to generic resolution).
- **Section 4 — Mandatory Medical Disclaimer:** Persistent boxed notice with warning icon and emergency contact reminder (112 / 911).

### 5.7 History List & Detail Screen
- **List View:** Chronological grouped list. Each row displays:
  - Modality icon badge (`multimodal`, `image`, `text`, `audio`).
  - Formatted relative timestamp (e.g., *"Today at 3:15 PM"*).
  - Verdict snippet (2 lines max).
  - Execution duration badge (e.g., `1.8s`).
- **Swipe Actions:** Swipe left reveals red **"Delete"** action with haptic confirmation.
- **Detail View:** Tapping any record rehydrates the full Results view for that historical snapshot.

### 5.8 Profile & Server Configuration Screen
- **User Account Card:** User display name, email address, registration date.
- **Server Connection Section:**
  - Base URL field (`http://192.168.1.100:8000`).
  - **"Test Connection"** trigger with live latency readout.
  - Explanation of local Wi-Fi connectivity.
- **Privacy & Safety Disclosures:** Clean grouped list linking to local data policy, medical disclaimers, and open-source licenses.
- **Sign Out Action:** High-contrast red destructive row with confirmation sheet.

---

## 6. Micro-Interactions & Haptic Feedback

- **Shutter Press:** Medium impact haptic (`UIImpactFeedbackGenerator(style: .medium)`).
- **Audio Recording Start/Stop:** Soft impact haptic (`UIImpactFeedbackGenerator(style: .soft)`).
- **Analysis Completion:** Success notification haptic (`UINotificationFeedbackGenerator().notificationOccurred(.success)`).
- **Clinical Error / Danger Verdict:** Warning notification haptic (`UINotificationFeedbackGenerator().notificationOccurred(.warning)`).
- **Accordion Toggle:** Light selection haptic (`UISelectionFeedbackGenerator().selectionChanged()`).

