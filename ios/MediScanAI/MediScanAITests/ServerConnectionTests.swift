import XCTest
import Foundation
@testable import MediScanAI

// MARK: - Server Connection & Wi-Fi Tests (WIFI-01 through WIFI-05)

final class ServerConnectionTests: XCTestCase {

    private var mockTransport: MockNetworkTransport!
    private var testDefaults: UserDefaults!
    private var config: NetworkConfiguration!
    private var networkClient: NetworkClient!
    private var connectionManager: ServerConnectionManager!

    @MainActor
    override func setUp() {
        super.setUp()
        testDefaults = UserDefaults(suiteName: "ServerConnectionTestsSuite")!
        testDefaults.removePersistentDomain(forName: "ServerConnectionTestsSuite")

        config = NetworkConfiguration(defaults: testDefaults)
        mockTransport = MockNetworkTransport()
        networkClient = NetworkClient(
            configuration: config,
            transport: mockTransport
        )
        connectionManager = ServerConnectionManager(
            networkClient: networkClient,
            configuration: config
        )
    }

    override func tearDown() {
        mockTransport = nil
        testDefaults?.removePersistentDomain(forName: "ServerConnectionTestsSuite")
        testDefaults = nil
        config = nil
        networkClient = nil
        connectionManager = nil
        super.tearDown()
    }

    // MARK: - 1. Server Configuration & URL Validation Tests (WIFI-01)

    func testValidLocalURLNormalization() {
        let rawURLString = "http://192.168.0.155:8000///"
        XCTAssertTrue(config.updateBaseURL(from: rawURLString))
        XCTAssertEqual(config.baseURL.absoluteString, "http://192.168.0.155:8000")
        XCTAssertNil(NetworkConfiguration.validationError(for: rawURLString))
    }

    func testInvalidURLDetection() {
        // Missing Scheme
        XCTAssertFalse(config.updateBaseURL(from: "192.168.0.155:8000"))
        XCTAssertNotNil(NetworkConfiguration.validationError(for: "192.168.0.155:8000"))

        // Unsupported Scheme (ftp)
        XCTAssertFalse(config.updateBaseURL(from: "ftp://192.168.0.155:8000"))
        XCTAssertNotNil(NetworkConfiguration.validationError(for: "ftp://192.168.0.155:8000"))

        // Missing Host
        XCTAssertFalse(config.updateBaseURL(from: "http://:8000"))
        XCTAssertNotNil(NetworkConfiguration.validationError(for: "http://:8000"))

        // Empty String
        XCTAssertFalse(config.updateBaseURL(from: ""))
        XCTAssertNotNil(NetworkConfiguration.validationError(for: ""))

        // Invalid Port (above 65535)
        XCTAssertFalse(config.updateBaseURL(from: "http://192.168.0.155:70000"))
        XCTAssertNotNil(NetworkConfiguration.validationError(for: "http://192.168.0.155:70000"))
    }

    func testConfigurationPersistenceAcrossInstances() {
        let newURLString = "http://192.168.1.50:8000"
        XCTAssertTrue(config.updateBaseURL(from: newURLString))

        // Create a new configuration instance with the same UserDefaults suite
        let restoredConfig = NetworkConfiguration(defaults: testDefaults)
        XCTAssertEqual(restoredConfig.baseURL.absoluteString, newURLString)
    }

    func testConfigurationResetToDefault() {
        config.updateBaseURL(from: "http://10.0.0.99:9000")
        XCTAssertEqual(config.baseURL.absoluteString, "http://10.0.0.99:9000")

        config.resetToDefault()
        XCTAssertEqual(config.baseURL.absoluteString, NetworkConfiguration.defaultBaseURLString)
    }

    // MARK: - 2. Connection Testing & Latency Reporting (WIFI-02)

    @MainActor
    func testCheckConnectionSuccessReportsLatency() async {
        let jsonResponse = """
        {"status":"alive","app":"MediScanAI","environment":"development","timestamp":1700000000.0}
        """

        mockTransport.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/health")
            XCTAssertEqual(request.httpMethod, "GET")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonResponse.data(using: .utf8)!, response)
        }

        let result = await connectionManager.checkConnection()
        XCTAssertTrue(result.isConnected)
        XCTAssertEqual(connectionManager.status, result)
        XCTAssertNotNil(connectionManager.lastCheckedAt)

        if case .connected(let latencyMs) = result {
            XCTAssertGreaterThanOrEqual(latencyMs, 0.0)
        } else {
            XCTFail("Expected .connected status with measured latency")
        }
    }

    @MainActor
    func testCheckConnectionUnhealthyStatus() async {
        let jsonResponse = """
        {"status":"degraded","app":"MediScanAI","environment":"development","timestamp":1700000000.0}
        """

        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonResponse.data(using: .utf8)!, response)
        }

        let result = await connectionManager.checkConnection()
        XCTAssertFalse(result.isConnected)
        if case .unreachable(let reason) = result {
            XCTAssertTrue(reason.contains("degraded"))
        } else {
            XCTFail("Expected .unreachable status for degraded health")
        }
    }

    @MainActor
    func testCheckConnectionTimeoutError() async {
        mockTransport.handler = { _ in
            throw APIError.timeout
        }

        let result = await connectionManager.checkConnection()
        XCTAssertFalse(result.isConnected)
        if case .unreachable(let reason) = result {
            XCTAssertTrue(reason.contains("timed out"))
        } else {
            XCTFail("Expected .unreachable status on timeout")
        }
    }

    @MainActor
    func testCheckConnectionNoNetworkConnection() async {
        mockTransport.handler = { _ in
            throw APIError.noConnection
        }

        let result = await connectionManager.checkConnection()
        XCTAssertFalse(result.isConnected)
        if case .unreachable(let reason) = result {
            XCTAssertTrue(reason.contains("No network connection"))
        } else {
            XCTFail("Expected .unreachable status on noConnection")
        }
    }

    @MainActor
    func testCheckConnectionServerError() async {
        mockTransport.handler = { _ in
            throw APIError.serverError(statusCode: 503, detail: "Backend starting up")
        }

        let result = await connectionManager.checkConnection()
        XCTAssertFalse(result.isConnected)
        if case .unreachable(let reason) = result {
            XCTAssertTrue(reason.contains("503"))
        } else {
            XCTFail("Expected .unreachable status on 503")
        }
    }

    @MainActor
    func testUpdateServerURLReTestsConnection() async {
        let jsonResponse = """
        {"status":"alive","app":"MediScanAI","environment":"development","timestamp":1700000000.0}
        """
        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonResponse.data(using: .utf8)!, response)
        }

        let newURL = URL(string: "http://192.168.1.120:8000")!
        let success = await connectionManager.updateServerURL(newURL)
        XCTAssertTrue(success)
        XCTAssertEqual(connectionManager.currentBaseURL.absoluteString, "http://192.168.1.120:8000")
        XCTAssertTrue(connectionManager.status.isConnected)
    }

    // MARK: - 3. Connection Status Taxonomy Tests (WIFI-03)

    func testServerConnectionStatusTaxonomy() {
        let unknown = ServerConnectionStatus.unknown
        XCTAssertFalse(unknown.isConnected)
        XCTAssertFalse(unknown.isChecking)
        XCTAssertEqual(unknown.statusDescription, "Unchecked")

        let checking = ServerConnectionStatus.checking
        XCTAssertFalse(checking.isConnected)
        XCTAssertTrue(checking.isChecking)
        XCTAssertEqual(checking.statusDescription, "Checking...")

        let connected = ServerConnectionStatus.connected(latencyMs: 14.2)
        XCTAssertTrue(connected.isConnected)
        XCTAssertFalse(connected.isChecking)
        XCTAssertEqual(connected.statusDescription, "Local Wi-Fi (14 ms)")

        let unreachable = ServerConnectionStatus.unreachable(reason: "Refused")
        XCTAssertFalse(unreachable.isConnected)
        XCTAssertFalse(unreachable.isChecking)
        XCTAssertEqual(unreachable.statusDescription, "Disconnected")
    }

    // MARK: - 4. Auth Session Isolation on Unreachable Backend (WIFI-05)

    @MainActor
    func testUnreachableBackendDoesNotInvalidateUserSession() async throws {
        let mockKeychain = MockKeychainStorage(initialToken: "valid_jwt_token")
        let authProvider = InMemoryAuthorizationHeaderProvider(initialToken: "valid_jwt_token")
        let authManager = AuthManager(
            networkClient: networkClient,
            keychain: mockKeychain,
            authProvider: authProvider
        )

        // Simulate failed connection check
        mockTransport.handler = { _ in
            throw APIError.timeout
        }

        await connectionManager.checkConnection()
        XCTAssertFalse(connectionManager.status.isConnected)

        // Keychain and token must NOT be purged simply because host is unreachable
        XCTAssertEqual(try mockKeychain.getToken(), "valid_jwt_token")
        XCTAssertEqual(authProvider.currentToken, "valid_jwt_token")
    }
}
