import Foundation
import SwiftUI

/// Central dependency container and runtime environment for MediScanAI iOS.
/// Provides configuration and dependency injection hooks for core services.
@Observable
public final class AppEnvironment {

    // MARK: - Application Metadata

    public let appName: String = "MediScanAI"
    public let appVersion: String = "1.0.0"
    public let buildNumber: String = "1"

    // MARK: - Core Networking Services

    public let networkConfiguration: NetworkConfiguration
    public let authProvider: AuthorizationHeaderProviding
    public let networkClient: NetworkClientProtocol
    public let networkMonitor: NetworkMonitoring

    /// Current base URL for server communications.
    public var defaultBaseURL: URL {
        networkConfiguration.baseURL
    }

    // MARK: - Initialization & Dependency Injection

    public init(
        networkConfiguration: NetworkConfiguration = NetworkConfiguration(),
        authProvider: AuthorizationHeaderProviding = InMemoryAuthorizationHeaderProvider(),
        networkClient: NetworkClientProtocol? = nil,
        networkMonitor: NetworkMonitoring = NetworkMonitor()
    ) {
        self.networkConfiguration = networkConfiguration
        self.authProvider = authProvider
        self.networkMonitor = networkMonitor

        if let injectedClient = networkClient {
            self.networkClient = injectedClient
        } else {
            self.networkClient = NetworkClient(
                configuration: networkConfiguration,
                transport: URLSessionTransport(),
                authProvider: authProvider
            )
        }
    }
}
