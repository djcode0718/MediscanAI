import SwiftUI

// MARK: - Notice Banner Variant

public enum NoticeBannerVariant {
    case emergency
    case disclaimer
    case warning

    public var icon: String {
        switch self {
        case .emergency: return "phone.fill"
        case .disclaimer: return "cross.case.fill"
        case .warning: return "exclamationmark.triangle.fill"
        }
    }

    public var accentColor: Color {
        switch self {
        case .emergency: return AppColors.statusDanger
        case .disclaimer: return AppColors.textSecondary
        case .warning: return AppColors.statusWarning
        }
    }

    public var fillColor: Color {
        switch self {
        case .emergency: return AppColors.statusDangerFill
        case .disclaimer: return AppColors.surfaceSecondary
        case .warning: return AppColors.statusWarningFill
        }
    }

    public var borderColor: Color {
        switch self {
        case .emergency: return AppColors.statusDangerBorder
        case .disclaimer: return AppColors.borderSubtle
        case .warning: return AppColors.statusWarningBorder
        }
    }
}

// MARK: - NoticeBanner Component

public struct NoticeBanner: View {
    public let variant: NoticeBannerVariant
    public let title: String
    public let message: String
    public let actionTitle: String?
    public let action: (() -> Void)?

    public init(
        variant: NoticeBannerVariant = .disclaimer,
        title: String,
        message: String,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.variant = variant
        self.title = title
        self.message = message
        self.actionTitle = actionTitle
        self.action = action
    }

    public var body: some View {
        HStack(alignment: .top, spacing: AppSpacing.standard) {
            Image(systemName: variant.icon)
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(variant.accentColor)
                .padding(.top, 2)

            VStack(alignment: .leading, spacing: AppSpacing.micro) {
                Text(title)
                    .font(.appHeadline)
                    .foregroundColor(AppColors.textPrimary)

                Text(message)
                    .font(.appSubheadline)
                    .foregroundColor(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)

                if let actionTitle = actionTitle, let action = action {
                    Button(action: {
                        HapticFeedback.shared.impact(.light)
                        action()
                    }) {
                        Text(actionTitle)
                            .font(.appSubheadline)
                            .fontWeight(.semibold)
                            .foregroundColor(variant.accentColor)
                            .padding(.top, AppSpacing.micro)
                    }
                }
            }

            Spacer(minLength: 0)
        }
        .padding(AppSpacing.standard)
        .background(variant.fillColor)
        .cornerRadius(AppRadius.large)
        .overlay(
            RoundedRectangle(cornerRadius: AppRadius.large)
                .stroke(variant.borderColor, lineWidth: 1)
        )
    }

    // MARK: - Pre-configured Emergency & Disclaimer Banners

    /// Standard legal medical disclaimer required on all clinical screens
    public static func standardDisclaimer() -> NoticeBanner {
        NoticeBanner(
            variant: .disclaimer,
            title: "Medical Information Notice",
            message: "MediScanAI provides AI-assisted pharmacotherapy insights for educational and informational purposes only. It is not a substitute for professional clinical diagnosis. In life-threatening emergencies, call 112 or 911 immediately."
        )
    }

    /// Acute emergency fast-path banner
    public static func emergencyAlert(action: (() -> Void)? = nil) -> NoticeBanner {
        NoticeBanner(
            variant: .emergency,
            title: "Emergency Medical Attention Required",
            message: "Your reported symptoms may indicate an acute medical emergency requiring immediate professional intervention.",
            actionTitle: "Call Emergency Services (112 / 911)",
            action: action
        )
    }
}
