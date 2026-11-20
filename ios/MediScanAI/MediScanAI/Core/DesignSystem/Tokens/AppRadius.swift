import Foundation

// MARK: - App Corner Radii Scale

public enum AppRadius {
    /// 4pt - Micro badges and nested inner tags
    public static let micro: CGFloat = 4

    /// 8pt - Small chips, badges, and tag pills
    public static let small: CGFloat = 8

    /// 12pt - Compact buttons, text fields, and icon containers
    public static let medium: CGFloat = 12

    /// 16pt - Standard surface cards and interactive list rows
    public static let large: CGFloat = 16

    /// 24pt - Modal bottom sheets and full-bleed action containers
    public static let modal: CGFloat = 24

    /// 999pt - Circular icon buttons and pill indicators
    public static let pill: CGFloat = 999
}
