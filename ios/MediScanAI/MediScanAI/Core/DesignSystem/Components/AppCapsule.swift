import SwiftUI

// MARK: - Clinical Verdict Status Enum

public enum ClinicalVerdictStatus: String, CaseIterable {
    case danger
    case success
    case warning
    case neutral

    public var title: String {
        switch self {
        case .danger: return "Not Suitable"
        case .success: return "Suitable"
        case .warning: return "Caution"
        case .neutral: return "Info"
        }
    }

    public var defaultIcon: String {
        switch self {
        case .danger: return "exclamationmark.octagon.fill"
        case .success: return "checkmark.circle.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .neutral: return "info.circle.fill"
        }
    }

    public var textColor: Color {
        switch self {
        case .danger: return AppColors.statusDanger
        case .success: return AppColors.statusSuccess
        case .warning: return AppColors.statusWarning
        case .neutral: return AppColors.textSecondary
        }
    }

    public var fillColor: Color {
        switch self {
        case .danger: return AppColors.statusDangerFill
        case .success: return AppColors.statusSuccessFill
        case .warning: return AppColors.statusWarningFill
        case .neutral: return AppColors.surfaceTertiary
        }
    }

    public var borderColor: Color {
        switch self {
        case .danger: return AppColors.statusDangerBorder
        case .success: return AppColors.statusSuccessBorder
        case .warning: return AppColors.statusWarningBorder
        case .neutral: return AppColors.borderSubtle
        }
    }
}

// MARK: - VerdictBadge / AppCapsule

public struct VerdictBadge: View {
    public let status: ClinicalVerdictStatus
    public let customText: String?
    public let customIcon: String?
    public let isProminent: Bool

    public init(
        status: ClinicalVerdictStatus,
        text: String? = nil,
        icon: String? = nil,
        isProminent: Bool = false
    ) {
        self.status = status
        self.customText = text
        self.customIcon = icon
        self.isProminent = isProminent
    }

    public var body: some View {
        HStack(spacing: AppSpacing.compact) {
            Image(systemName: customIcon ?? status.defaultIcon)
                .font(.system(size: isProminent ? 16 : 12, weight: .bold))

            Text(customText ?? status.title)
                .font(isProminent ? .appHeadline : .appCaption1)
                .fontWeight(.semibold)
        }
        .foregroundColor(status.textColor)
        .padding(.horizontal, isProminent ? AppSpacing.standard : AppSpacing.compact + AppSpacing.micro)
        .padding(.vertical, isProminent ? AppSpacing.compact : AppSpacing.micro + 2)
        .background(status.fillColor)
        .cornerRadius(AppRadius.pill)
        .overlay(
            RoundedRectangle(cornerRadius: AppRadius.pill)
                .stroke(status.borderColor, lineWidth: 1)
        )
    }
}

// MARK: - MediaChip Component

public struct MediaChip: View {
    public let icon: String
    public let title: String
    public let subtitle: String?
    public let onRemove: (() -> Void)?

    public init(
        icon: String,
        title: String,
        subtitle: String? = nil,
        onRemove: (() -> Void)? = nil
    ) {
        self.icon = icon
        self.title = title
        self.subtitle = subtitle
        self.onRemove = onRemove
    }

    public var body: some View {
        HStack(spacing: AppSpacing.compact) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppColors.iconPrimary)

            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.appCaption1)
                    .foregroundColor(AppColors.textPrimary)
                    .lineLimit(1)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.appFootnote)
                        .foregroundColor(AppColors.textTertiary)
                        .lineLimit(1)
                }
            }

            if let onRemove = onRemove {
                Button(action: {
                    HapticFeedback.shared.impact(.light)
                    onRemove()
                }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(AppColors.textSecondary)
                        .padding(AppSpacing.micro)
                        .background(AppColors.surfaceElevated)
                        .clipShape(Circle())
                }
            }
        }
        .padding(.horizontal, AppSpacing.small)
        .padding(.vertical, AppSpacing.compact)
        .background(AppColors.surfaceTertiary)
        .cornerRadius(AppRadius.small)
        .overlay(
            RoundedRectangle(cornerRadius: AppRadius.small)
                .stroke(AppColors.borderSubtle, lineWidth: 1)
        )
    }
}

// MARK: - Alias
public typealias AppCapsule = VerdictBadge
