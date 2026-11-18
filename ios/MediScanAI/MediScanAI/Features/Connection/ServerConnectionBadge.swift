import SwiftUI

// MARK: - Server Connection Badge (WIFI-03)

/// Compact, tap-interactive status capsule designed for header integration.
/// Displays real-time backend reachability and opens ServerConfigSheet on tap.
public struct ServerConnectionBadge: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var showConfigSheet: Bool = false

    public init() {}

    public var body: some View {
        Button(action: {
            HapticFeedback.shared.impact(.light)
            showConfigSheet = true
        }) {
            HStack(spacing: AppSpacing.compact) {
                // Status Indicator Dot or Spinner
                indicatorView

                // Status Label
                Text(badgeLabel)
                    .font(.appCaption1)
                    .fontWeight(.medium)
                    .foregroundColor(AppColors.textPrimary)

                // Miniature Chevron indicating tap action
                Image(systemName: "chevron.right")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundColor(AppColors.textTertiary)
            }
            .padding(.horizontal, AppSpacing.standard)
            .padding(.vertical, AppSpacing.compact)
            .background(AppColors.surfaceSecondary)
            .cornerRadius(AppRadius.pill)
            .overlay(
                RoundedRectangle(cornerRadius: AppRadius.pill)
                    .stroke(borderColor, lineWidth: 1)
            )
        }
        .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.96))
        .accessibilityLabel("Server connection status: \(badgeLabel)")
        .accessibilityHint("Tap to configure Mac backend server URL")
        .accessibilityIdentifier("ServerConnectionBadge_Button")
        .sheet(isPresented: $showConfigSheet) {
            ServerConfigSheet()
        }
    }

    // MARK: - Subviews

    @ViewBuilder
    private var indicatorView: some View {
        switch environment.serverConnectionManager.status {
        case .connected:
            Circle()
                .fill(AppColors.statusSuccess)
                .frame(width: 8, height: 8)
                .accessibilityIdentifier("ServerConnectionBadge_ConnectedDot")

        case .unreachable:
            Circle()
                .fill(AppColors.statusDanger)
                .frame(width: 8, height: 8)
                .accessibilityIdentifier("ServerConnectionBadge_DisconnectedDot")

        case .checking:
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: AppColors.textPrimary))
                .scaleEffect(0.6)
                .frame(width: 8, height: 8)
                .accessibilityIdentifier("ServerConnectionBadge_CheckingSpinner")

        case .unknown:
            Circle()
                .fill(AppColors.textTertiary)
                .frame(width: 8, height: 8)
                .accessibilityIdentifier("ServerConnectionBadge_UnknownDot")
        }
    }

    private var badgeLabel: String {
        switch environment.serverConnectionManager.status {
        case .connected:
            return "Local Wi-Fi"
        case .unreachable:
            return "Disconnected"
        case .checking:
            return "Checking..."
        case .unknown:
            return "Server Offline"
        }
    }

    private var borderColor: Color {
        switch environment.serverConnectionManager.status {
        case .connected:
            return AppColors.statusSuccessBorder
        case .unreachable:
            return AppColors.statusDangerBorder
        case .checking, .unknown:
            return AppColors.borderSubtle
        }
    }
}
