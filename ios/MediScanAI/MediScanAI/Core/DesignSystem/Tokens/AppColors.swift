import SwiftUI

// MARK: - Color Hex Initializer

extension Color {
    /// Initialize a SwiftUI Color from a hexadecimal string (e.g. "#000000", "0A0A0A", "#F43F5E").
    init(hex: String) {
        let cleanHex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: cleanHex).scanHexInt64(&int)

        let a, r, g, b: UInt64
        switch cleanHex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255.0,
            green: Double(g) / 255.0,
            blue: Double(b) / 255.0,
            opacity: Double(a) / 255.0
        )
    }
}

// MARK: - Design System Color Tokens

public enum AppColors {
    // MARK: Monochromatic OLED Surface Tokens
    /// Canvas base layer for all fullscreen views (true OLED black #000000)
    public static let background = Color(hex: "#000000")

    /// Primary container sections and list row backgrounds (#0A0A0A)
    public static let surfacePrimary = Color(hex: "#0A0A0A")

    /// Grouped cards, input containers, and unselected controls (#141414)
    public static let surfaceSecondary = Color(hex: "#141414")

    /// Hovered or active inputs, chips, and selected states (#1E1E1E)
    public static let surfaceTertiary = Color(hex: "#1E1E1E")

    /// Modals, bottom sheets, and floating action sheets (#262626)
    public static let surfaceElevated = Color(hex: "#262626")

    /// Restrained 1px dividers and card borders (#2A2A2A)
    public static let borderSubtle = Color(hex: "#2A2A2A")

    /// Focused text inputs and active viewfinder reticles (#404040)
    public static let borderFocus = Color(hex: "#404040")

    // MARK: Text & Iconography Tokens
    /// Headlines, primary labels, and user inputs (#FFFFFF, 21:1 contrast)
    public static let textPrimary = Color(hex: "#FFFFFF")

    /// Explanatory paragraphs, section captions, and subheadings (#A1A1A1, 9.8:1 contrast)
    public static let textSecondary = Color(hex: "#A1A1A1")

    /// Timestamps, metadata labels, and input placeholders (#707070, 4.8:1 contrast)
    public static let textTertiary = Color(hex: "#707070")

    /// Action icons, navigation triggers, and back buttons (#F5F5F5)
    public static let iconPrimary = Color(hex: "#F5F5F5")

    /// Auxiliary icons, chevron disclosures, and trailing indicators (#929292)
    public static let iconSecondary = Color(hex: "#929292")

    /// Primary call-to-action button fill (#FFFFFF) with inverted black text
    public static let accentNeutral = Color(hex: "#FFFFFF")

    /// Disabled controls and inactive state tint (#484848)
    public static let disabled = Color(hex: "#484848")

    // MARK: Semantic Clinical Status Tokens
    // Danger / Not Suitable / Acute Emergency
    public static let statusDanger = Color(hex: "#F43F5E")
    public static let statusDangerFill = Color(hex: "#2D0A14")
    public static let statusDangerBorder = Color(hex: "#5C1D2C")

    // Success / Suitable / Matched Indications
    public static let statusSuccess = Color(hex: "#10B981")
    public static let statusSuccessFill = Color(hex: "#06281E")
    public static let statusSuccessBorder = Color(hex: "#0D5C45")

    // Warning / Caution / Inconclusive Evidence
    public static let statusWarning = Color(hex: "#F59E0B")
    public static let statusWarningFill = Color(hex: "#2E1E05")
    public static let statusWarningBorder = Color(hex: "#5C4010")

    // MARK: Hex String Constants (for testing & verification)
    public enum Hex {
        public static let background = "#000000"
        public static let surfacePrimary = "#0A0A0A"
        public static let surfaceSecondary = "#141414"
        public static let surfaceTertiary = "#1E1E1E"
        public static let surfaceElevated = "#262626"
        public static let borderSubtle = "#2A2A2A"
        public static let borderFocus = "#404040"
        public static let textPrimary = "#FFFFFF"
        public static let textSecondary = "#A1A1A1"
        public static let textTertiary = "#707070"
        public static let iconPrimary = "#F5F5F5"
        public static let iconSecondary = "#929292"
        public static let accentNeutral = "#FFFFFF"
        public static let disabled = "#484848"
        public static let statusDanger = "#F43F5E"
        public static let statusDangerFill = "#2D0A14"
        public static let statusDangerBorder = "#5C1D2C"
        public static let statusSuccess = "#10B981"
        public static let statusSuccessFill = "#06281E"
        public static let statusSuccessBorder = "#0D5C45"
        public static let statusWarning = "#F59E0B"
        public static let statusWarningFill = "#2E1E05"
        public static let statusWarningBorder = "#5C4010"
    }
}
