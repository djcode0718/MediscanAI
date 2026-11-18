import SwiftUI

// MARK: - Connection Failure Recovery View (WIFI-05)

/// Actionable offline recovery component presented when network requests or health checks fail.
/// Guides the user through local Wi-Fi diagnosis and configuration without signing them out.
public struct ConnectionFailureRecoveryView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var showConfigSheet: Bool = false

    public let customMessage: String?
    public let onRetry: (() -> Void)?

    public init(
        customMessage: String? = nil,
        onRetry: (() -> Void)? = nil
    ) {
        self.customMessage = customMessage
        self.onRetry = onRetry
    }

    public var body: some View {
        AppCard {
            VStack(alignment: .leading, spacing: AppSpacing.large) {
                // Warning Notice Banner
                NoticeBanner(
                    variant: .warning,
                    title: "Mac Backend Unreachable",
                    message: customMessage ?? "Cannot reach Mac backend. Ensure your iPhone is on the same Wi-Fi network and the backend is running."
                )
                .accessibilityIdentifier("ConnectionRecovery_WarningBanner")

                // Diagnostic Steps Checklist
                VStack(alignment: .leading, spacing: AppSpacing.compact) {
                    Text("Troubleshooting Steps:")
                        .font(.appSubheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(AppColors.textPrimary)

                    diagnosticCheckItem(
                        icon: "wifi",
                        text: "Verify both iPhone and Mac are on the same Wi-Fi network."
                    )

                    diagnosticCheckItem(
                        icon: "terminal.fill",
                        text: "Confirm the Mac backend is running (`uvicorn backend.main:app --host 0.0.0.0 --port 8000`)."
                    )

                    diagnosticCheckItem(
                        icon: "network",
                        text: "Check if the Mac DHCP IP has changed (`ipconfig getifaddr en0`)."
                    )

                    diagnosticCheckItem(
                        icon: "hand.raised.fill",
                        text: "Ensure 'Local Network' permission is allowed in iOS Settings → MediScanAI."
                    )
                }

                AppDivider()

                // Action Buttons
                VStack(spacing: AppSpacing.compact) {
                    PrimaryButton(
                        "Retry Connection",
                        icon: "arrow.clockwise",
                        isLoading: environment.serverConnectionManager.isTesting
                    ) {
                        if let customRetry = onRetry {
                            customRetry()
                        } else {
                            Task {
                                await environment.serverConnectionManager.checkConnection()
                            }
                        }
                    }
                    .accessibilityIdentifier("ConnectionRecovery_RetryButton")

                    SecondaryButton("Configure Server URL", icon: "gearshape") {
                        showConfigSheet = true
                    }
                    .accessibilityIdentifier("ConnectionRecovery_ConfigButton")
                }
            }
        }
        .accessibilityIdentifier("ConnectionRecovery_Card")
        .sheet(isPresented: $showConfigSheet) {
            ServerConfigSheet()
        }
    }

    private func diagnosticCheckItem(icon: String, text: String) -> some View {
        HStack(alignment: .top, spacing: AppSpacing.compact) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppColors.textSecondary)
                .frame(width: 18, height: 18)
                .padding(.top, 1)

            Text(text)
                .font(.appFootnote)
                .foregroundColor(AppColors.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
