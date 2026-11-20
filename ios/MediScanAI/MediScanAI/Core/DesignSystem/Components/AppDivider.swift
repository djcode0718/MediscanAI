import SwiftUI

// MARK: - AppDivider

public struct AppDivider: View {
    public let color: Color
    public let height: CGFloat
    public let horizontalPadding: CGFloat

    public init(
        color: Color = AppColors.borderSubtle,
        height: CGFloat = 1,
        horizontalPadding: CGFloat = 0
    ) {
        self.color = color
        self.height = height
        self.horizontalPadding = horizontalPadding
    }

    public var body: some View {
        Rectangle()
            .fill(color)
            .frame(height: height)
            .padding(.horizontal, horizontalPadding)
    }
}
