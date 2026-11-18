import SwiftUI

// MARK: - Scan Tab Placeholder (Phase 6 Placeholder for Phase 7)

public struct ScanPlaceholderView: View {
    public init() {}

    public var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            VStack(spacing: AppSpacing.large) {
                // Header with Connection Badge
                HStack {
                    VStack(alignment: .leading, spacing: AppSpacing.micro) {
                        Text("Medicine Scan")
                            .font(.appTitle2)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Capture label or packaging")
                            .font(.appCaption1)
                            .foregroundColor(AppColors.textSecondary)
                    }

                    Spacer()

                    ServerConnectionBadge()
                }
                .padding(.horizontal, AppSpacing.extraLarge)
                .padding(.top, AppSpacing.standard)

                Spacer()

                // Hero Center Card
                VStack(spacing: AppSpacing.standard) {
                    ZStack {
                        Circle()
                            .fill(AppColors.surfaceSecondary)
                            .frame(width: 96, height: 96)
                            .overlay(
                                Circle()
                                    .stroke(AppColors.borderSubtle, lineWidth: 1)
                            )

                        Image(systemName: "camera.viewfinder")
                            .font(.system(size: 44, weight: .light))
                            .foregroundColor(AppColors.textPrimary)
                    }

                    VStack(spacing: AppSpacing.compact) {
                        Text("Medicine Label Scanner")
                            .font(.appTitle3)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Hardware AVFoundation camera capture, photo library picker, and PaddleOCR text extraction will be activated in Phase 7.")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, AppSpacing.standard)
                    }

                    // Roadmap Phase Capsule
                    HStack(spacing: AppSpacing.compact) {
                        Circle()
                            .fill(AppColors.statusSuccess)
                            .frame(width: 6, height: 6)

                        Text("Phase 7 · Core Scanning Engine")
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
                                Capsule()
                                    .stroke(AppColors.borderSubtle, lineWidth: 1)
                            )
                    )
                }
                .padding(AppSpacing.extraLarge)

                Spacer()
            }
        }
        .accessibilityIdentifier("ScanPlaceholderView")
    }
}
