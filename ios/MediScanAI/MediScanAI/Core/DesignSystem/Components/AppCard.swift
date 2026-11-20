import SwiftUI

// MARK: - AppCard / SurfaceCard

public struct AppCard<Content: View>: View {
    public let backgroundColor: Color
    public let borderColor: Color
    public let cornerRadius: CGFloat
    public let padding: CGFloat
    public let content: Content

    public init(
        backgroundColor: Color = AppColors.surfaceSecondary,
        borderColor: Color = AppColors.borderSubtle,
        cornerRadius: CGFloat = AppRadius.large,
        padding: CGFloat = AppSpacing.standard,
        @ViewBuilder content: () -> Content
    ) {
        self.backgroundColor = backgroundColor
        self.borderColor = borderColor
        self.cornerRadius = cornerRadius
        self.padding = padding
        self.content = content()
    }

    public var body: some View {
        content
            .padding(padding)
            .background(backgroundColor)
            .cornerRadius(cornerRadius)
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(borderColor, lineWidth: 1)
            )
    }
}

// MARK: - Interactive AppCard

public struct InteractiveAppCard<Content: View>: View {
    public let action: () -> Void
    public let content: Content

    public init(
        action: @escaping () -> Void,
        @ViewBuilder content: () -> Content
    ) {
        self.action = action
        self.content = content()
    }

    public var body: some View {
        Button(action: {
            HapticFeedback.shared.impact(.light)
            action()
        }) {
            AppCard {
                content
            }
        }
        .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.99))
    }
}

// MARK: - Alias for spec naming

public typealias SurfaceCard<Content: View> = AppCard<Content>
