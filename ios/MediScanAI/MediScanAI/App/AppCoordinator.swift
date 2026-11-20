import Foundation
import SwiftUI

/// App-level navigation and state coordinator.
/// Directs the root user flow between initial launch, authentication, and core features.
@Observable
public final class AppCoordinator {

    public enum RootDestination: Equatable {
        case foundation
        case restoringSession
        case authentication
        case authenticated
        #if DEBUG
        case designSystemPreview
        #endif
    }

    public var currentDestination: RootDestination = .foundation
    public var selectedTab: AppTab = .home

    public init() {}

    public func selectTab(_ tab: AppTab) {
        selectedTab = tab
    }

    public func resetToFoundation() {
        currentDestination = .foundation
    }

    public func navigateToAuthentication() {
        currentDestination = .authentication
    }

    public func navigateToAuthenticated() {
        currentDestination = .authenticated
    }

    #if DEBUG
    public func navigateToDesignSystemPreview() {
        currentDestination = .designSystemPreview
    }
    #endif
}
