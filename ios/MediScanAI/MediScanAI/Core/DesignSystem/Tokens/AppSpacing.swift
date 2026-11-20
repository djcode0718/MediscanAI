import Foundation

// MARK: - App Spacing Scale (4pt Grid)

public enum AppSpacing {
    /// 4pt - Micro padding (inside badges and pills)
    public static let micro: CGFloat = 4

    /// 8pt - Compact gap (between icon and label, chip spacing)
    public static let compact: CGFloat = 8

    /// 12pt - Small gap (between form fields, list item vertical padding)
    public static let small: CGFloat = 12

    /// 16pt - Standard gap (card interior padding, standard gutters)
    public static let standard: CGFloat = 16

    /// 20pt - Large gap (screen horizontal margins on standard iPhones)
    public static let large: CGFloat = 20

    /// 24pt - Screen horizontal margins on Plus/Pro Max devices; section separators
    public static let extraLarge: CGFloat = 24

    /// 32pt - Major section rhythm
    public static let section: CGFloat = 32

    /// 48pt - Screen header and footer clearances
    public static let clearance: CGFloat = 48
}
