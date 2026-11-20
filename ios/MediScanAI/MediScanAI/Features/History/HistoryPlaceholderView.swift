import SwiftUI

// MARK: - History Tab Placeholder (Phase 6 Placeholder for Phase 10)

public struct HistoryPlaceholderView: View {
    public init() {}

    public var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            VStack(spacing: AppSpacing.large) {
                // Header with Connection Badge
                HStack {
                    VStack(alignment: .leading, spacing: AppSpacing.micro) {
                        Text("Analysis History")
                            .font(.appTitle2)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Comprehensive clinical logs")
                            .font(.appCaption1)
                            .foregroundColor(AppColors.textSecondary)
                    }

                    Spacer()

                    ServerConnectionBadge()
                }
                .padding(.horizontal, AppSpacing.extraLarge)
                .padding(.top, AppSpacing.standard)

                Spacer()

                // Center Card
                VStack(spacing: AppSpacing.standard) {
                    ZStack {
                        Circle()
                            .fill(AppColors.surfaceSecondary)
                            .frame(width: 96, height: 96)
                            .overlay(
                                Circle()
                                    .stroke(AppColors.borderSubtle, lineWidth: 1)
                            )

                        Image(systemName: "clock")
                            .font(.system(size: 44, weight: .light))
                            .foregroundColor(AppColors.textPrimary)
                    }

                    VStack(spacing: AppSpacing.compact) {
                        Text("Clinical Records Timeline")
                            .font(.appTitle3)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Paginated analysis archive, deletion controls, and search filtering will be activated in Phase 10.")
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

                        Text("Phase 10 · History & Timeline")
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
        .accessibilityIdentifier("HistoryPlaceholderView")
    }
}
