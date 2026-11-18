import Foundation
import SwiftUI

/// Central dependency container and runtime environment for MediScanAI iOS.
/// Provides configuration and dependency injection hooks for core services.
@Observable
public final class AppEnvironment: Sendable {
    
    // MARK: - Application Metadata
    
    public let appName: String = "MediScanAI"
    public let appVersion: String = "1.0.0"
    public let buildNumber: String = "1"
    
    // MARK: - Server Configuration Placeholder
    
    /// Default development host URL on local Wi-Fi.
    public var defaultBaseURL: URL {
        URL(string: "http://192.168.0.155:8000")!
    }
    
    // MARK: - Initialization
    
    public init() {
        // Core services will be instantiated and registered here in future phases.
    }
}

