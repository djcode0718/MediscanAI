import SwiftUI

// MARK: - Design System Showcase & Preview View

public struct DesignSystemPreviewView: View {
    @State private var sampleText: String = "Paracetamol 500mg"
    @State private var samplePassword: String = "SecretPass123"
    @State private var sampleSymptoms: String = "Mild headache and low-grade fever starting yesterday evening."
    @State private var sampleError: String? = "Invalid medicine packaging photo or unreadable text"
    @State private var buttonTapCount: Int = 0
    @State private var isButtonLoading: Bool = false
    @State private var stagedProgress: Double = 0.65

    public init() {}

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: AppSpacing.section) {
                    // Header
                    VStack(alignment: .leading, spacing: AppSpacing.compact) {
                        Text("Design System")
                            .font(.appLargeTitle)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Monochromatic OLED Component Library (Phase 2)")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    .padding(.top, AppSpacing.small)

                    AppDivider()

                    // Section 1: Color Palette
                    colorPaletteSection

                    AppDivider()

                    // Section 2: Typography Scale
                    typographySection

                    AppDivider()

                    // Section 3: Spacing & Radii
                    spacingAndRadiiSection

                    AppDivider()

                    // Section 4: Buttons
                    buttonsSection

                    AppDivider()

                    // Section 5: Surface Cards
                    cardsSection

                    AppDivider()

                    // Section 6: Form Controls & Inputs
                    formInputsSection

                    AppDivider()

                    // Section 7: Status Capsules & Badges
                    capsulesAndBadgesSection

                    AppDivider()

                    // Section 8: Loading & Staged Inference
                    loadingIndicatorsSection

                    AppDivider()

                    // Section 9: Notice & Medical Disclaimer Banners
                    noticeBannersSection

                    AppDivider()

                    // Section 10: Empty State
                    emptyStateSection
                }
                .padding(.horizontal, AppSpacing.standard)
                .padding(.bottom, AppSpacing.clearance)
            }
            .background(AppColors.background.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Design Tokens & UI")
                        .font(.appHeadline)
                        .foregroundColor(AppColors.textPrimary)
                }
            }
        }
        .accessibilityIdentifier("DesignSystemPreviewView")
    }

    // MARK: - 1. Color Palette Section
    private var colorPaletteSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Color Tokens", subtitle: "True-black OLED (#000000) & tonal elevation")

            Text("Surfaces & Borders")
                .font(.appHeadline)
                .foregroundColor(AppColors.textSecondary)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: AppSpacing.compact) {
                    colorChip("Base", AppColors.background, hex: AppColors.Hex.background, border: AppColors.borderSubtle)
                    colorChip("Surface 1", AppColors.surfacePrimary, hex: AppColors.Hex.surfacePrimary, border: AppColors.borderSubtle)
                    colorChip("Surface 2", AppColors.surfaceSecondary, hex: AppColors.Hex.surfaceSecondary)
                    colorChip("Surface 3", AppColors.surfaceTertiary, hex: AppColors.Hex.surfaceTertiary)
                    colorChip("Elevated", AppColors.surfaceElevated, hex: AppColors.Hex.surfaceElevated)
                    colorChip("Border Sub", AppColors.borderSubtle, hex: AppColors.Hex.borderSubtle)
                    colorChip("Border Foc", AppColors.borderFocus, hex: AppColors.Hex.borderFocus)
                }
            }

            Text("Clinical Status Accents")
                .font(.appHeadline)
                .foregroundColor(AppColors.textSecondary)

            HStack(spacing: AppSpacing.compact) {
                statusChip("Danger", AppColors.statusDanger, hex: AppColors.Hex.statusDanger)
                statusChip("Success", AppColors.statusSuccess, hex: AppColors.Hex.statusSuccess)
                statusChip("Warning", AppColors.statusWarning, hex: AppColors.Hex.statusWarning)
            }
        }
    }

    private func colorChip(_ name: String, _ color: Color, hex: String, border: Color? = nil) -> some View {
        VStack(spacing: AppSpacing.micro) {
            RoundedRectangle(cornerRadius: AppRadius.small)
                .fill(color)
                .frame(width: 68, height: 48)
                .overlay(
                    RoundedRectangle(cornerRadius: AppRadius.small)
                        .stroke(border ?? AppColors.borderSubtle, lineWidth: 1)
                )

            Text(name)
                .font(.appFootnote)
                .foregroundColor(AppColors.textPrimary)

            Text(hex)
                .font(.appCaption1)
                .foregroundColor(AppColors.textTertiary)
                .monospacedDigit()
        }
    }

    private func statusChip(_ name: String, _ color: Color, hex: String) -> some View {
        VStack(spacing: AppSpacing.micro) {
            RoundedRectangle(cornerRadius: AppRadius.small)
                .fill(color)
                .frame(maxWidth: .infinity)
                .frame(height: 38)

            Text(name)
                .font(.appFootnote)
                .foregroundColor(AppColors.textPrimary)

            Text(hex)
                .font(.appCaption1)
                .foregroundColor(AppColors.textTertiary)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - 2. Typography Section
    private var typographySection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Typography Scale", subtitle: "San Francisco Pro with Dynamic Type")

            Group {
                Text("Large Title 34pt Bold").font(.appLargeTitle).foregroundColor(AppColors.textPrimary)
                Text("Title 1 28pt Semibold").font(.appTitle1).foregroundColor(AppColors.textPrimary)
                Text("Title 2 22pt Semibold").font(.appTitle2).foregroundColor(AppColors.textPrimary)
                Text("Title 3 20pt Medium").font(.appTitle3).foregroundColor(AppColors.textPrimary)
                Text("Headline 17pt Semibold").font(.appHeadline).foregroundColor(AppColors.textPrimary)
                Text("Body 17pt Regular - Clinical rationale and interaction text.").font(.appBody).foregroundColor(AppColors.textSecondary)
                Text("Callout 16pt Regular - Immediate warnings and triage tags.").font(.appCallout).foregroundColor(AppColors.textSecondary)
                Text("Subheadline 15pt Regular - Metadata and dates.").font(.appSubheadline).foregroundColor(AppColors.textTertiary)
                Text("Footnote 13pt Regular - Legal disclaimers.").font(.appFootnote).foregroundColor(AppColors.textTertiary)
                Text("Caption 1 12pt Medium - Tags and Pills").font(.appCaption1).foregroundColor(AppColors.textTertiary)
                Text("Tabular Figures: 124.50 ms | 98.4% Match | 00:14").font(.appFootnote).monospacedDigit().foregroundColor(AppColors.textPrimary)
            }
        }
    }

    // MARK: - 3. Spacing & Radii Section
    private var spacingAndRadiiSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Spacing & Radii", subtitle: "4pt rhythm: 4, 8, 12, 16, 20, 24, 32, 48pt")

            HStack(spacing: AppSpacing.compact) {
                radiiBadge("Small 8pt", AppRadius.small)
                radiiBadge("Medium 12pt", AppRadius.medium)
                radiiBadge("Large 16pt", AppRadius.large)
                radiiBadge("Modal 24pt", AppRadius.modal)
            }
        }
    }

    private func radiiBadge(_ label: String, _ radius: CGFloat) -> some View {
        Text(label)
            .font(.appCaption1)
            .foregroundColor(AppColors.textSecondary)
            .padding(.horizontal, AppSpacing.compact)
            .padding(.vertical, AppSpacing.micro + 2)
            .background(AppColors.surfaceTertiary)
            .cornerRadius(radius)
            .overlay(
                RoundedRectangle(cornerRadius: radius)
                    .stroke(AppColors.borderSubtle, lineWidth: 1)
            )
            .frame(maxWidth: .infinity)
    }

    // MARK: - 4. Buttons Section
    private var buttonsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Buttons", subtitle: "Primary, secondary, destructive, disabled & icon triggers")

            PrimaryButton("Primary Action (Inverted White)", icon: "sparkles") {
                buttonTapCount += 1
            }
            .accessibilityIdentifier("Preview_PrimaryButton")

            HStack(spacing: AppSpacing.standard) {
                SecondaryButton("Secondary Action", icon: "doc.text") {
                    buttonTapCount += 1
                }
                .accessibilityIdentifier("Preview_SecondaryButton")

                AppButton("Destructive", icon: "trash", variant: .destructive) {
                    buttonTapCount += 1
                }
                .accessibilityIdentifier("Preview_DestructiveButton")
            }

            HStack(spacing: AppSpacing.standard) {
                PrimaryButton("Loading State", isLoading: true) {}
                SecondaryButton("Disabled State", isEnabled: false) {}
            }

            HStack(spacing: AppSpacing.standard) {
                IconButton(icon: "camera.fill") { buttonTapCount += 1 }
                IconButton(icon: "mic.fill") { buttonTapCount += 1 }
                IconButton(icon: "photo.on.rectangle.angled") { buttonTapCount += 1 }
                IconButton(icon: "gearshape.fill") { buttonTapCount += 1 }

                Spacer()

                Text("Taps: \(buttonTapCount)")
                    .font(.appFootnote)
                    .foregroundColor(AppColors.textSecondary)
                    .monospacedDigit()
                    .accessibilityIdentifier("Preview_TapCounter")
            }
        }
    }

    // MARK: - 5. Cards Section
    private var cardsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Surface Cards", subtitle: "Tonal background #141414 with 1px border #2A2A2A")

            AppCard {
                VStack(alignment: .leading, spacing: AppSpacing.compact) {
                    HStack {
                        Image(systemName: "cross.case.fill")
                            .foregroundColor(AppColors.textPrimary)
                        Text("Clinical Analysis Snapshot")
                            .font(.appHeadline)
                            .foregroundColor(AppColors.textPrimary)
                        Spacer()
                        VerdictBadge(status: .success)
                    }

                    Text("Paracetamol 500mg matches reported mild tension headache. No contraindications detected in clinical RAG database.")
                        .font(.appBody)
                        .foregroundColor(AppColors.textSecondary)
                }
            }
            .accessibilityIdentifier("Preview_SampleCard")

            InteractiveAppCard(action: {
                buttonTapCount += 1
            }) {
                HStack {
                    VStack(alignment: .leading, spacing: AppSpacing.micro) {
                        Text("Interactive Surface Card")
                            .font(.appHeadline)
                            .foregroundColor(AppColors.textPrimary)
                        Text("Supports tap gesture, haptic feedback and 0.99 scale press animation.")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundColor(AppColors.iconSecondary)
                }
            }
            .accessibilityIdentifier("Preview_InteractiveCard")
        }
    }

    // MARK: - 6. Form Inputs Section
    private var formInputsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Form Controls", subtitle: "High contrast inputs with focus state & inline validation")

            AppTextField(
                title: "Medicine or Molecule Name",
                placeholder: "e.g. Paracetamol or Amoxicillin",
                text: $sampleText,
                leadingIcon: "pills.fill"
            )
            .accessibilityIdentifier("Preview_TextField")

            AppTextField(
                title: "Password",
                placeholder: "Enter account password",
                text: $samplePassword,
                leadingIcon: "lock.fill",
                isSecure: true
            )
            .accessibilityIdentifier("Preview_PasswordField")

            AppTextEditor(
                title: "Describe Symptoms & Condition",
                placeholder: "Enter details about your symptoms...",
                text: $sampleSymptoms,
                minHeight: 90
            )
            .accessibilityIdentifier("Preview_MultilineField")

            AppTextField(
                title: "Input with Error Validation",
                placeholder: "Packaging barcode",
                text: .constant(""),
                leadingIcon: "barcode.viewfinder",
                errorMessage: sampleError
            )
            .accessibilityIdentifier("Preview_ErrorField")
        }
    }

    // MARK: - 7. Capsules & Verdict Badges Section
    private var capsulesAndBadgesSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Verdict Badges", subtitle: "Semantic clinical status pills")

            HStack(spacing: AppSpacing.compact) {
                VerdictBadge(status: .danger)
                    .accessibilityIdentifier("Preview_VerdictDanger")
                VerdictBadge(status: .warning)
                    .accessibilityIdentifier("Preview_VerdictWarning")
                VerdictBadge(status: .success)
                    .accessibilityIdentifier("Preview_VerdictSuccess")
                VerdictBadge(status: .neutral)
            }

            Text("Prominent Verdict Banners")
                .font(.appHeadline)
                .foregroundColor(AppColors.textSecondary)

            VerdictBadge(
                status: .danger,
                text: "Not Suitable for Reported Symptoms",
                icon: "exclamationmark.octagon.fill",
                isProminent: true
            )

            VerdictBadge(
                status: .success,
                text: "Clinically Suitable / Expected Match",
                icon: "checkmark.circle.fill",
                isProminent: true
            )

            Text("Attached Media Chips")
                .font(.appHeadline)
                .foregroundColor(AppColors.textSecondary)

            HStack(spacing: AppSpacing.compact) {
                MediaChip(icon: "photo.fill", title: "packaging_label.jpg", subtitle: "2.4 MB") {}
                MediaChip(icon: "waveform", title: "symptom_voice.m4a", subtitle: "00:14") {}
            }
        }
    }

    // MARK: - 8. Loading Indicators Section
    private var loadingIndicatorsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Loading & Inference State", subtitle: "Dual-concentric white ring spinner with staged progress")

            AppStageLoadingView(
                stageText: "Extracting packaging label with PaddleOCR...",
                progress: stagedProgress
            )
            .background(AppColors.surfaceSecondary)
            .cornerRadius(AppRadius.large)
            .overlay(
                RoundedRectangle(cornerRadius: AppRadius.large)
                    .stroke(AppColors.borderSubtle, lineWidth: 1)
            )
            .accessibilityIdentifier("Preview_LoadingStage")
        }
    }

    // MARK: - 9. Notice & Disclaimer Banners Section
    private var noticeBannersSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Notice Banners", subtitle: "Disclaimers and emergency fast-path triggers")

            NoticeBanner.emergencyAlert {
                HapticFeedback.shared.warning()
            }
            .accessibilityIdentifier("Preview_EmergencyBanner")

            NoticeBanner.standardDisclaimer()
                .accessibilityIdentifier("Preview_DisclaimerBanner")
        }
    }

    // MARK: - 10. Empty State Section
    private var emptyStateSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            AppSectionHeader("Empty State", subtitle: "Calm placeholder for zero-data views")

            AppCard {
                AppEmptyState(
                    icon: "clock.arrow.circlepath",
                    title: "No Previous Analyses",
                    message: "Scan medicine packaging or record symptoms to see clinical assessments saved here.",
                    actionTitle: "Start New Scan"
                ) {
                    buttonTapCount += 1
                }
            }
            .accessibilityIdentifier("Preview_EmptyState")
        }
    }
}

#Preview {
    DesignSystemPreviewView()
}
