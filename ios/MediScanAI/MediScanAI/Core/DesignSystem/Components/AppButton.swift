import SwiftUI

// MARK: - Button Style Variants

public enum AppButtonStyleVariant {
    case primary
    case secondary
    case destructive
    case ghost
}

// MARK: - App Button Scale Pressed Style

public struct AppScaleButtonStyle: ButtonStyle {
    public let scaleAmount: CGFloat

    public init(scaleAmount: CGFloat = 0.98) {
        self.scaleAmount = scaleAmount
    }

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? scaleAmount : 1.0)
            .animation(.easeInOut(duration: 0.15), value: configuration.isPressed)
    }
}

// MARK: - AppButton

public struct AppButton: View {
    public let title: String
    public let icon: String?
    public let variant: AppButtonStyleVariant
    public let isLoading: Bool
    public let isEnabled: Bool
    public let fullWidth: Bool
    public let action: () -> Void

    public init(
        _ title: String,
        icon: String? = nil,
        variant: AppButtonStyleVariant = .primary,
        isLoading: Bool = false,
        isEnabled: Bool = true,
        fullWidth: Bool = true,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.variant = variant
        self.isLoading = isLoading
        self.isEnabled = isEnabled
        self.fullWidth = fullWidth
        self.action = action
    }

    public var body: some View {
        Button(action: {
            guard isEnabled && !isLoading else { return }
            HapticFeedback.shared.impact(.light)
            action()
        }) {
            HStack(spacing: AppSpacing.compact) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: foregroundColor))
                        .scaleEffect(0.9)
                } else {
                    if let icon = icon {
                        Image(systemName: icon)
                            .font(.system(size: 16, weight: .semibold))
                    }
                    Text(title)
                        .font(.appHeadline)
                }
            }
            .foregroundColor(foregroundColor)
            .frame(maxWidth: fullWidth ? .infinity : nil)
            .frame(minHeight: 50)
            .padding(.horizontal, AppSpacing.standard)
            .background(backgroundView)
            .cornerRadius(AppRadius.medium)
            .overlay(borderOverlay)
            .opacity(isEnabled ? 1.0 : 0.45)
        }
        .disabled(!isEnabled || isLoading)
        .buttonStyle(AppScaleButtonStyle())
        .accessibilityLabel(title)
    }

    @ViewBuilder
    private var backgroundView: some View {
        switch variant {
        case .primary:
            AppColors.accentNeutral
        case .secondary:
            AppColors.surfaceTertiary
        case .destructive:
            AppColors.statusDangerFill
        case .ghost:
            Color.clear
        }
    }

    private var foregroundColor: Color {
        switch variant {
        case .primary:
            return AppColors.background
        case .secondary:
            return AppColors.textPrimary
        case .destructive:
            return AppColors.statusDanger
        case .ghost:
            return AppColors.textSecondary
        }
    }

    @ViewBuilder
    private var borderOverlay: some View {
        switch variant {
        case .primary:
            EmptyView()
        case .secondary:
            RoundedRectangle(cornerRadius: AppRadius.medium)
                .stroke(AppColors.borderSubtle, lineWidth: 1)
        case .destructive:
            RoundedRectangle(cornerRadius: AppRadius.medium)
                .stroke(AppColors.statusDangerBorder, lineWidth: 1)
        case .ghost:
            EmptyView()
        }
    }
}

// MARK: - Specialized Convenience Buttons

public struct PrimaryButton: View {
    public let title: String
    public let icon: String?
    public let isLoading: Bool
    public let isEnabled: Bool
    public let action: () -> Void

    public init(
        _ title: String,
        icon: String? = nil,
        isLoading: Bool = false,
        isEnabled: Bool = true,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.isLoading = isLoading
        self.isEnabled = isEnabled
        self.action = action
    }

    public var body: some View {
        AppButton(
            title,
            icon: icon,
            variant: .primary,
            isLoading: isLoading,
            isEnabled: isEnabled,
            action: action
        )
    }
}

public struct SecondaryButton: View {
    public let title: String
    public let icon: String?
    public let isLoading: Bool
    public let isEnabled: Bool
    public let action: () -> Void

    public init(
        _ title: String,
        icon: String? = nil,
        isLoading: Bool = false,
        isEnabled: Bool = true,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.isLoading = isLoading
        self.isEnabled = isEnabled
        self.action = action
    }

    public var body: some View {
        AppButton(
            title,
            icon: icon,
            variant: .secondary,
            isLoading: isLoading,
            isEnabled: isEnabled,
            action: action
        )
    }
}

public struct IconButton: View {
    public let icon: String
    public let size: CGFloat
    public let action: () -> Void

    public init(
        icon: String,
        size: CGFloat = 44,
        action: @escaping () -> Void
    ) {
        self.icon = icon
        self.size = size
        self.action = action
    }

    public var body: some View {
        Button(action: {
            HapticFeedback.shared.impact(.light)
            action()
        }) {
            Image(systemName: icon)
                .font(.system(size: size * 0.42, weight: .semibold))
                .foregroundColor(AppColors.iconPrimary)
                .frame(width: size, height: size)
                .background(AppColors.surfaceSecondary)
                .clipShape(Circle())
                .overlay(
                    Circle().stroke(AppColors.borderSubtle, lineWidth: 1)
                )
        }
        .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.94))
    }
}
