import SwiftUI

// MARK: - Symptom Composer Placeholder Sheet (NAV-03)

public struct SymptomComposerPlaceholderSheet: View {
    @Environment(\.dismiss) private var dismiss

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()

                VStack(spacing: AppSpacing.large) {
                    Spacer()

                    ZStack {
                        Circle()
                            .fill(AppColors.surfaceSecondary)
                            .frame(width: 88, height: 88)
                            .overlay(
                                Circle().stroke(AppColors.borderSubtle, lineWidth: 1)
                            )

                        Image(systemName: "text.badge.plus")
                            .font(.system(size: 38, weight: .light))
                            .foregroundColor(AppColors.textPrimary)
                    }

                    VStack(spacing: AppSpacing.compact) {
                        Text("Symptom Description")
                            .font(.appTitle2)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Interactive symptom entry, clinical severity tagging, and contraindication reasoning will be activated in Phase 8.")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, AppSpacing.standard)
                    }

                    HStack(spacing: AppSpacing.compact) {
                        Circle()
                            .fill(AppColors.statusSuccess)
                            .frame(width: 6, height: 6)

                        Text("Phase 8 · Symptom Analysis")
                            .font(.appCaption1)
                            .monospacedDigit()
                            .foregroundColor(AppColors.textTertiary)
                    }
                    .padding(.horizontal, AppSpacing.standard)
                    .padding(.vertical, AppSpacing.compact)
                    .background(
                        Capsule()
                            .fill(AppColors.surfacePrimary)
                            .overlay(
                                Capsule().stroke(AppColors.borderSubtle, lineWidth: 1)
                            )
                    )

                    Spacer()

                    PrimaryButton("Close", icon: "xmark") {
                        dismiss()
                    }
                    .padding(.bottom, AppSpacing.extraLarge)
                }
                .padding(.horizontal, AppSpacing.extraLarge)
            }
            .navigationTitle("Symptoms")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.textPrimary)
                    .accessibilityIdentifier("SymptomComposer_DoneButton")
                }
            }
        }
        .accessibilityIdentifier("SymptomComposerPlaceholderSheet")
    }
}
