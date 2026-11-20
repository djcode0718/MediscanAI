import SwiftUI

// MARK: - Voice Recording Placeholder Sheet (NAV-03)

public struct VoiceRecordingPlaceholderSheet: View {
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

                        Image(systemName: "waveform")
                            .font(.system(size: 38, weight: .light))
                            .foregroundColor(AppColors.textPrimary)
                    }

                    VStack(spacing: AppSpacing.compact) {
                        Text("Voice Consultation")
                            .font(.appTitle2)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Microphone audio capture, Whisper speech-to-text transcription, and voice-guided triage will be activated in Phase 8.")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, AppSpacing.standard)
                    }

                    HStack(spacing: AppSpacing.compact) {
                        Circle()
                            .fill(AppColors.statusSuccess)
                            .frame(width: 6, height: 6)

                        Text("Phase 8 · Audio Transcription")
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
            .navigationTitle("Voice Recording")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.textPrimary)
                    .accessibilityIdentifier("VoiceRecording_DoneButton")
                }
            }
        }
        .accessibilityIdentifier("VoiceRecordingPlaceholderSheet")
    }
}
