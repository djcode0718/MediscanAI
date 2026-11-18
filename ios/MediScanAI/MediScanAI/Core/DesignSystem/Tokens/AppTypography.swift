import SwiftUI

// MARK: - App Typography System

public enum AppTypography {
    /// Large Title: Bold, 34pt, screen titles
    public static let largeTitle: Font = .system(size: 34, weight: .bold, design: .default)

    /// Title 1: Semibold, 28pt, modal sheet headers
    public static let title1: Font = .system(size: 28, weight: .semibold, design: .default)

    /// Title 2: Semibold, 22pt, verdict headlines and section cards
    public static let title2: Font = .system(size: 22, weight: .semibold, design: .default)

    /// Title 3: Medium, 20pt, sub-section headings
    public static let title3: Font = .system(size: 20, weight: .medium, design: .default)

    /// Headline: Semibold, 17pt, card headers, list item titles
    public static let headline: Font = .system(size: 17, weight: .semibold, design: .default)

    /// Body: Regular, 17pt, primary clinical explanation text
    public static let body: Font = .system(size: 17, weight: .regular, design: .default)

    /// Callout: Regular, 16pt, high-priority warnings, notes
    public static let callout: Font = .system(size: 16, weight: .regular, design: .default)

    /// Subheadline: Regular, 15pt, secondary metadata, dates
    public static let subheadline: Font = .system(size: 15, weight: .regular, design: .default)

    /// Footnote: Regular, 13pt, legal disclaimers, timing badges
    public static let footnote: Font = .system(size: 13, weight: .regular, design: .default)

    /// Caption 1: Medium, 12pt, modality pills, tags, status
    public static let caption1: Font = .system(size: 12, weight: .medium, design: .default)

    /// Monospaced Numbers (for metrics, durations, and percentages)
    public static func monospaced(_ font: Font) -> Font {
        font.monospacedDigit()
    }
}

// MARK: - Font Extension for Fluent Usage

extension Font {
    public static let appLargeTitle = AppTypography.largeTitle
    public static let appTitle1 = AppTypography.title1
    public static let appTitle2 = AppTypography.title2
    public static let appTitle3 = AppTypography.title3
    public static let appHeadline = AppTypography.headline
    public static let appBody = AppTypography.body
    public static let appCallout = AppTypography.callout
    public static let appSubheadline = AppTypography.subheadline
    public static let appFootnote = AppTypography.footnote
    public static let appCaption1 = AppTypography.caption1
}

// MARK: - View Modifiers for Dynamic Type Tracking & Leading

public struct AppTextStyleModifier: ViewModifier {
    public enum Style {
        case largeTitle
        case title1
        case title2
        case title3
        case headline
        case body
        case callout
        case subheadline
        case footnote
        case caption1
    }

    public let style: Style
    public let monospaced: Bool

    public init(style: Style, monospaced: Bool = false) {
        self.style = style
        self.monospaced = monospaced
    }

    public func body(content: Content) -> some View {
        let baseFont: Font = {
            switch style {
            case .largeTitle: return .appLargeTitle
            case .title1: return .appTitle1
            case .title2: return .appTitle2
            case .title3: return .appTitle3
            case .headline: return .appHeadline
            case .body: return .appBody
            case .callout: return .appCallout
            case .subheadline: return .appSubheadline
            case .footnote: return .appFootnote
            case .caption1: return .appCaption1
            }
        }()

        let font = monospaced ? baseFont.monospacedDigit() : baseFont

        let tracking: CGFloat = {
            switch style {
            case .largeTitle: return 0.37
            case .title1: return 0.36
            case .title2: return 0.35
            case .title3: return 0.38
            case .headline: return -0.41
            case .body: return -0.41
            case .callout: return -0.32
            case .subheadline: return -0.24
            case .footnote: return -0.08
            case .caption1: return 0.00
            }
        }()

        let lineSpacing: CGFloat = {
            switch style {
            case .largeTitle: return 7
            case .title1: return 6
            case .title2: return 6
            case .title3: return 5
            case .headline: return 5
            case .body: return 5
            case .callout: return 5
            case .subheadline: return 5
            case .footnote: return 5
            case .caption1: return 4
            }
        }()

        content
            .font(font)
            .tracking(tracking)
            .lineSpacing(lineSpacing)
    }
}

extension View {
    public func appTextStyle(_ style: AppTextStyleModifier.Style, monospaced: Bool = false) -> some View {
        modifier(AppTextStyleModifier(style: style, monospaced: monospaced))
    }
}
