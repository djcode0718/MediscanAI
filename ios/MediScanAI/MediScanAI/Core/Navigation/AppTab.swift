import SwiftUI

// MARK: - App Navigation Tab (NAV-01)

public enum AppTab: String, CaseIterable, Identifiable, Hashable {
    case home
    case scan
    case history
    case profile

    public var id: String { rawValue }

    public var title: String {
        switch self {
        case .home:
            return "Home"
        case .scan:
            return "Scan"
        case .history:
            return "History"
        case .profile:
            return "Profile"
        }
    }

    public var icon: String {
        switch self {
        case .home:
            return "house"
        case .scan:
            return "camera.viewfinder"
        case .history:
            return "clock"
        case .profile:
            return "person"
        }
    }
}
