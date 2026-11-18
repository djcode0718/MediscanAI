import SwiftUI

// MARK: - AppSectionHeader

public struct AppSectionHeader: View {
    public let title: String
    public let subtitle: String?
    public let actionTitle: String?
    public let action: (() -> Void)?

    public init(
        _ title: String,
        subtitle: String? = nil,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.title = title
        self.subtitle = subtitle
        self.actionTitle = actionTitle
        self.action = action
    }

    public var body: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.appHeadline)
                    .foregroundColor(AppColors.textPrimary)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.appSubheadline)
                        .foregroundColor(AppColors.textSecondary)
                }
            }

            Spacer()

            if let actionTitle = actionTitle, let action = action {
                Button(action: {
                    HapticFeedback.shared.impact(.light)
                    action()
                }) {
                    Text(actionTitle)
                        .font(.appSubheadline)
                        .fontWeight(.medium)
                        .foregroundColor(AppColors.textSecondary)
                }
            }
        }
        .padding(.vertical, AppSpacing.micro)
    }
}
