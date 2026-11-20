import UIKit

// MARK: - Haptic Feedback Controller

public final class HapticFeedback {
    public static let shared = HapticFeedback()

    private init() {}

    /// Trigger tactile feedback for shutter capture
    public func shutter() {
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.prepare()
        generator.impactOccurred()
    }

    /// Trigger tactile feedback for audio recording start / stop
    public func recording() {
        let generator = UIImpactFeedbackGenerator(style: .soft)
        generator.prepare()
        generator.impactOccurred()
    }

    /// Trigger tactile feedback for light impacts (buttons, tabs)
    public func impact(_ style: UIImpactFeedbackGenerator.FeedbackStyle = .light) {
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.prepare()
        generator.impactOccurred()
    }

    /// Trigger tactile feedback for selection changes (accordion toggle, picker)
    public func selection() {
        let generator = UISelectionFeedbackGenerator()
        generator.prepare()
        generator.selectionChanged()
    }

    /// Trigger tactile feedback for clinical success or completion
    public func success() {
        let generator = UINotificationFeedbackGenerator()
        generator.prepare()
        generator.notificationOccurred(.success)
    }

    /// Trigger tactile feedback for clinical warning or danger verdicts
    public func warning() {
        let generator = UINotificationFeedbackGenerator()
        generator.prepare()
        generator.notificationOccurred(.warning)
    }

    /// Trigger tactile feedback for validation or network errors
    public func error() {
        let generator = UINotificationFeedbackGenerator()
        generator.prepare()
        generator.notificationOccurred(.error)
    }
}
