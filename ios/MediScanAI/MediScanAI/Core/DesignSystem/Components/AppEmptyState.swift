import SwiftUI

// MARK: - AppEmptyState

public struct AppEmptyState: View {
    public let icon: String
    public let title: String
    public let message: String
    public let actionTitle: String?
    public let action: (() -> Void)?

    public init(
        icon: String = "tray",
        title: String,
        message: String,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.icon = icon
        self.title = title
        self.message = message
        self.actionTitle = actionTitle
        self.action = action
    }

    public var body: some View {
        VStack(spacing: AppSpacing.standard) {
            Image(systemName: icon)
                .font(.system(size: 44, weight: .light))
                .foregroundColor(AppColors.textTertiary)
                .padding(.bottom, AppSpacing.micro)

            VStack(spacing: AppSpacing.compact) {
                Text(title)
                    .font(.appHeadline)
                    .foregroundColor(AppColors.textPrimary)
                    .multilineTextAlignment(.center)

                Text(message)
                    .font(.appBody)
                    .foregroundColor(AppColors.textSecondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, AppSpacing.standard)
            }

            if let actionTitle = actionTitle, let action = action {
                SecondaryButton(actionTitle, action: action)
                    .frame(maxWidth: 220)
                    .padding(.top, AppSpacing.compact)
            }
        }
        .padding(AppSpacing.section)
        .frame(maxWidth: .infinity)
    }
}
