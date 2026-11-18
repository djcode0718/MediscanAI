import Foundation
import os

// MARK: - Server Connection Managing Protocol

public protocol ServerConnectionManaging: AnyObject {
    var status: ServerConnectionStatus { get }
    var lastCheckedAt: Date? { get }
    var isTesting: Bool { get }
    var currentBaseURL: URL { get }

    func checkConnection() async -> ServerConnectionStatus
    func updateServerURL(_ url: URL) async -> Bool
    func resetToDefault() async
}

// MARK: - Native Server Connection Manager (WIFI-01, WIFI-02, WIFI-04)

@Observable
public final class ServerConnectionManager: ServerConnectionManaging {
    public private(set) var status: ServerConnectionStatus = .unknown
    public private(set) var lastCheckedAt: Date? = nil
    public private(set) var isTesting: Bool = false

    public let networkClient: NetworkClientProtocol
    public let configuration: NetworkConfiguration
    public let networkMonitor: NetworkMonitoring

    private let logger = Logger(subsystem: "ai.mediscan.ios", category: "ServerConnectionManager")

    public var currentBaseURL: URL {
        configuration.baseURL
    }

    public init(
        networkClient: NetworkClientProtocol,
        configuration: NetworkConfiguration,
        networkMonitor: NetworkMonitoring = NetworkMonitor()
    ) {
        self.networkClient = networkClient
        self.configuration = configuration
        self.networkMonitor = networkMonitor
    }

    /// Execute health probe against backend to determine reachability and measure round-trip latency.
    /// Prevents overlapping concurrent requests.
    @discardableResult
    public func checkConnection() async -> ServerConnectionStatus {
        guard !isTesting else {
            logger.debug("Health check already in progress, returning current status.")
            return status
        }

        isTesting = true
        status = .checking
        logger.info("Executing server health check against \(self.configuration.baseURL.absoluteString, privacy: .public)...")

        do {
            let (health, latency) = try await networkClient.checkHealth()
            lastCheckedAt = Date()
            isTesting = false

            if health.isAlive {
                let roundedLatency = (latency * 10).rounded() / 10
                status = .connected(latencyMs: roundedLatency)
                logger.info("Server connection established (\(roundedLatency, privacy: .public) ms).")
            } else {
                let reason = "Server reported unhealthy status: '\(health.status)'"
                status = .unreachable(reason: reason)
                logger.warning("\(reason, privacy: .public)")
            }
            return status
        } catch let apiError as APIError {
            lastCheckedAt = Date()
            isTesting = false

            let reason: String
            switch apiError {
            case .timeout:
                reason = "Connection timed out. Check that your Mac and iPhone are on the same Wi-Fi and that port 8000 is open."
            case .noConnection:
                reason = "No network connection detected on device. Check your Wi-Fi settings."
            case .serverError(let code, let detail):
                reason = "Server returned error (\(code)): \(detail ?? "Internal error")"
            case .invalidURL:
                reason = "Configured server URL is invalid."
            case .badRequest(let detail):
                reason = "Bad request to health probe: \(detail ?? "Unknown")"
            default:
                reason = "Cannot reach Mac backend. Ensure the backend server is running and your Mac LAN IP is correct."
            }

            status = .unreachable(reason: reason)
            logger.error("Server connection check failed: \(reason, privacy: .public)")
            return status
        } catch {
            lastCheckedAt = Date()
            isTesting = false
            let reason = "Cannot reach Mac backend. Ensure your iPhone is on the same Wi-Fi network and the backend is running."
            status = .unreachable(reason: reason)
            logger.error("Server check failed with error: \(error.localizedDescription, privacy: .public)")
            return status
        }
    }

    /// Update configured base URL and immediately test connection.
    @discardableResult
    public func updateServerURL(_ url: URL) async -> Bool {
        guard configuration.updateBaseURL(url) else {
            return false
        }
        logger.info("Updated server URL to \(url.absoluteString, privacy: .public). Testing connectivity...")
        await checkConnection()
        return true
    }

    /// Reset base URL to default and re-test.
    public func resetToDefault() async {
        configuration.resetToDefault()
        logger.info("Reset server URL to default (\(self.configuration.baseURL.absoluteString, privacy: .public)).")
        await checkConnection()
    }
}

// MARK: - Mock Server Connection Manager (for previews and deterministic tests)

public final class MockServerConnectionManager: ServerConnectionManaging {
    public var status: ServerConnectionStatus
    public var lastCheckedAt: Date?
    public var isTesting: Bool = false
    public var currentBaseURL: URL
    public var shouldSucceed: Bool = true
    public var latencyToReturn: Double = 14.5
    public var failureReasonToReturn: String = "Cannot reach Mac backend."

    public init(
        initialStatus: ServerConnectionStatus = .unknown,
        baseURL: URL = URL(string: "http://192.168.0.155:8000")!
    ) {
        self.status = initialStatus
        self.currentBaseURL = baseURL
    }

    public func checkConnection() async -> ServerConnectionStatus {
        isTesting = true
        status = .checking
        try? await Task.sleep(nanoseconds: 50_000_000) // 50ms synthetic delay
        isTesting = false
        lastCheckedAt = Date()

        if shouldSucceed {
            status = .connected(latencyMs: latencyToReturn)
        } else {
            status = .unreachable(reason: failureReasonToReturn)
        }
        return status
    }

    public func updateServerURL(_ url: URL) async -> Bool {
        self.currentBaseURL = url
        _ = await checkConnection()
        return true
    }

    public func resetToDefault() async {
        self.currentBaseURL = URL(string: NetworkConfiguration.defaultBaseURLString)!
        _ = await checkConnection()
    }
}
