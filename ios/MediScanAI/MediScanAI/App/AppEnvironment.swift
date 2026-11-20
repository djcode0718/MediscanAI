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
    public let keychain: KeychainStorageProtocol
    public let authManager: AuthManager
    public let serverConnectionManager: ServerConnectionManager

    /// Current base URL for server communications.
    public var defaultBaseURL: URL {
        networkConfiguration.baseURL
    }

    // MARK: - Initialization & Dependency Injection

    public init(
        networkConfiguration: NetworkConfiguration = NetworkConfiguration(),
        authProvider: AuthorizationHeaderProviding = InMemoryAuthorizationHeaderProvider(),
        keychain: KeychainStorageProtocol = KeychainStorage(),
        networkClient: NetworkClientProtocol? = nil,
        networkMonitor: NetworkMonitoring = NetworkMonitor(),
        authManager: AuthManager? = nil,
        serverConnectionManager: ServerConnectionManager? = nil
    ) {
        self.networkConfiguration = networkConfiguration
        self.authProvider = authProvider
        self.keychain = keychain
        self.networkMonitor = networkMonitor

        let client = networkClient ?? NetworkClient(
            configuration: networkConfiguration,
            transport: URLSessionTransport(),
            authProvider: authProvider
        )
        self.networkClient = client

        let manager = authManager ?? AuthManager(
            networkClient: client,
            keychain: keychain,
            authProvider: authProvider
        )
        self.authManager = manager

        let connManager = serverConnectionManager ?? ServerConnectionManager(
            networkClient: client,
            configuration: networkConfiguration,
            networkMonitor: networkMonitor
        )
        self.serverConnectionManager = connManager

        // Wire 401 automatic session revocation (AUTH-05)
        client.onUnauthorized = { [weak manager] in
            Task { @MainActor in
                manager?.handleUnauthorized()
            }
        }
    }
}
