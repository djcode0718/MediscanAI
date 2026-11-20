import XCTest
import Foundation
@testable import MediScanAI

// MARK: - Authentication Unit Tests (AUTH-01 through AUTH-07)

final class AuthenticationTests: XCTestCase {

    private var mockTransport: MockNetworkTransport!
    private var mockKeychain: MockKeychainStorage!
    private var authProvider: InMemoryAuthorizationHeaderProvider!
    private var networkClient: NetworkClient!
    private var authManager: AuthManager!

    override func setUp() {
        super.setUp()
        mockTransport = MockNetworkTransport()
        mockKeychain = MockKeychainStorage()
        authProvider = InMemoryAuthorizationHeaderProvider()
        networkClient = NetworkClient(
            transport: mockTransport,
            authProvider: authProvider
        )
        authManager = AuthManager(
            networkClient: networkClient,
            keychain: mockKeychain,
            authProvider: authProvider
        )

        networkClient.onUnauthorized = { [weak authManager] in
            Task { @MainActor in
                authManager?.handleUnauthorized()
            }
        }
    }

    override func tearDown() {
        mockTransport = nil
        mockKeychain = nil
        authProvider = nil
        networkClient = nil
        authManager = nil
        super.tearDown()
    }

    // MARK: - 1. Keychain Storage Tests (AUTH-01)

    func testMockKeychainSaveAndRetrieve() throws {
        XCTAssertNil(try mockKeychain.getToken())
        try mockKeychain.saveToken("sample_jwt_token_123")
        XCTAssertEqual(try mockKeychain.getToken(), "sample_jwt_token_123")
    }

    func testMockKeychainOverwriteToken() throws {
        try mockKeychain.saveToken("token_v1")
        XCTAssertEqual(try mockKeychain.getToken(), "token_v1")
        try mockKeychain.saveToken("token_v2")
        XCTAssertEqual(try mockKeychain.getToken(), "token_v2")
    }

    func testMockKeychainDeleteToken() throws {
        try mockKeychain.saveToken("to_be_deleted")
        XCTAssertNotNil(try mockKeychain.getToken())
        try mockKeychain.deleteToken()
        XCTAssertNil(try mockKeychain.getToken())
    }

    func testMockKeychainErrorPropagation() {
        mockKeychain.shouldThrowError = .duplicateItem
        XCTAssertThrowsError(try mockKeychain.saveToken("failing_token")) { error in
            XCTAssertEqual(error as? KeychainError, KeychainError.duplicateItem)
        }
    }

    func testRealKeychainStorageInitialization() {
        let realKeychain = KeychainStorage(service: "ai.mediscan.ios.test", account: "test_token")
        XCTAssertEqual(realKeychain.service, "ai.mediscan.ios.test")
        XCTAssertEqual(realKeychain.account, "test_token")
    }

    // MARK: - 2. AuthManager Initial State (AUTH-02)

    func testAuthManagerInitialState() {
        XCTAssertEqual(authManager.state, .unauthenticated)
        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(authManager.currentUser)
        XCTAssertFalse(authManager.isRestoringSession)
    }

    // MARK: - 3. Login Tests (AUTH-04)

    @MainActor
    func testLoginSuccessPersistsTokenAndUpdatesState() async throws {
        let jsonResponse = """
        {"access_token":"login_test_token_jwt","token_type":"bearer","user":{"id":42,"email":"doctor@hospital.org","full_name":"Dr. House","is_active":true,"is_superuser":false,"created_at":"2026-01-01T00:00:00Z"}}
        """

        mockTransport.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/auth/login")
            XCTAssertEqual(request.httpMethod, "POST")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonResponse.data(using: .utf8)!, response)
        }

        let user = try await authManager.login(email: "doctor@hospital.org", password: "password123")
        XCTAssertEqual(user.id, 42)
        XCTAssertEqual(user.email, "doctor@hospital.org")
        XCTAssertEqual(user.fullName, "Dr. House")
        XCTAssertTrue(authManager.isAuthenticated)
        XCTAssertEqual(authManager.currentUser?.id, 42)
        XCTAssertEqual(try mockKeychain.getToken(), "login_test_token_jwt")
        XCTAssertEqual(authProvider.currentToken, "login_test_token_jwt")
    }

    @MainActor
    func testLoginFailureThrowsErrorAndClearsState() async {
        let jsonError = """
        {"detail":"Invalid email or password"}
        """

        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 401,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonError.data(using: .utf8)!, response)
        }

        do {
            _ = try await authManager.login(email: "wrong@email.com", password: "badpassword")
            XCTFail("Login should fail for invalid credentials")
        } catch let apiError as APIError {
            XCTAssertEqual(apiError, .unauthorized(detail: "Invalid email or password"))
        } catch {
            XCTFail("Unexpected error type: \(error)")
        }

        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(try? mockKeychain.getToken())
        XCTAssertNil(authProvider.currentToken)
    }

    // MARK: - 4. Registration Tests (AUTH-03)

    @MainActor
    func testRegisterSuccessPersistsTokenAndUpdatesState() async throws {
        let jsonResponse = """
        {"access_token":"register_token_jwt","token_type":"bearer","user":{"id":77,"email":"newuser@mediscan.ai","full_name":"Sarah Connor","is_active":true,"is_superuser":false,"created_at":"2026-01-01T00:00:00Z"}}
        """

        mockTransport.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/auth/register")
            XCTAssertEqual(request.httpMethod, "POST")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 201,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonResponse.data(using: .utf8)!, response)
        }

        let user = try await authManager.register(
            email: "newuser@mediscan.ai",
            password: "password123",
            fullName: "Sarah Connor"
        )
        XCTAssertEqual(user.id, 77)
        XCTAssertEqual(user.email, "newuser@mediscan.ai")
        XCTAssertTrue(authManager.isAuthenticated)
        XCTAssertEqual(try mockKeychain.getToken(), "register_token_jwt")
        XCTAssertEqual(authProvider.currentToken, "register_token_jwt")
    }

    @MainActor
    func testRegisterFailureThrowsBadRequest() async {
        let jsonError = """
        {"detail":"An account with this email address is already registered."}
        """

        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 400,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonError.data(using: .utf8)!, response)
        }

        do {
            _ = try await authManager.register(email: "existing@test.com", password: "password123")
            XCTFail("Registration should fail for duplicate email")
        } catch let apiError as APIError {
            XCTAssertEqual(apiError, .badRequest(detail: "An account with this email address is already registered."))
        } catch {
            XCTFail("Unexpected error type: \(error)")
        }

        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(try? mockKeychain.getToken())
    }

    // MARK: - 5. Session Restoration Tests (AUTH-05)

    @MainActor
    func testRestoreSessionWithValidToken() async throws {
        try mockKeychain.saveToken("valid_persisted_token")

        let jsonUser = """
        {"id":100,"email":"restored@hospital.org","full_name":"Dr. Restored","is_active":true,"is_superuser":false,"created_at":"2026-01-01T00:00:00Z"}
        """

        mockTransport.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/auth/me")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer valid_persisted_token")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonUser.data(using: .utf8)!, response)
        }

        await authManager.restoreSession()

        XCTAssertTrue(authManager.isAuthenticated)
        XCTAssertEqual(authManager.currentUser?.email, "restored@hospital.org")
        XCTAssertEqual(authProvider.currentToken, "valid_persisted_token")
    }

    @MainActor
    func testRestoreSessionWithExpiredTokenWipesKeychain() async throws {
        try mockKeychain.saveToken("expired_token")

        let jsonError = """
        {"detail":"Could not validate credentials"}
        """

        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 401,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (jsonError.data(using: .utf8)!, response)
        }

        await authManager.restoreSession()

        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(try mockKeychain.getToken())
        XCTAssertNil(authProvider.currentToken)
    }

    @MainActor
    func testRestoreSessionWithEmptyKeychain() async {
        await authManager.restoreSession()

        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(authProvider.currentToken)
        XCTAssertEqual(mockTransport.recordedRequests.count, 0)
    }

    // MARK: - 6. Logout & Unauthorized Handling (AUTH-02, AUTH-05)

    @MainActor
    func testExplicitLogoutClearsStateAndKeychain() throws {
        try mockKeychain.saveToken("active_session_token")
        authProvider.setToken("active_session_token")
        let session = UserSession(
            token: "active_session_token",
            user: UserResponse(id: 1, email: "user@test.com")
        )
        // Manually place in authenticated state via private setter emulation or login
        authManager.handleUnauthorized() // Initially unauthenticated, shouldn't crash

        authManager.logout()
        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(try mockKeychain.getToken())
        XCTAssertNil(authProvider.currentToken)
    }

    @MainActor
    func testHandleUnauthorizedEvictsSession() throws {
        try mockKeychain.saveToken("stale_token")
        authProvider.setToken("stale_token")

        // First transition to authenticated
        let jsonResponse = """
        {"access_token":"stale_token","token_type":"bearer","user":{"id":1,"email":"test@test.com","is_active":true,"is_superuser":false,"created_at":"2026-01-01T00:00:00Z"}}
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

        Task {
            _ = try await authManager.login(email: "test@test.com", password: "password")
        }

        // Wait brief tick for login to finish
        let expectation = expectation(description: "Session restored")
        Task {
            _ = try await authManager.login(email: "test@test.com", password: "password")
            expectation.fulfill()
        }
        wait(for: [expectation], timeout: 1.0)

        XCTAssertTrue(authManager.isAuthenticated)

        // Now trigger handleUnauthorized
        authManager.handleUnauthorized()

        XCTAssertFalse(authManager.isAuthenticated)
        XCTAssertNil(try mockKeychain.getToken())
        XCTAssertNil(authProvider.currentToken)

        // Multiple calls must not crash or cause duplicate storms
        authManager.handleUnauthorized()
        XCTAssertFalse(authManager.isAuthenticated)
    }

    // MARK: - 7. AuthenticationViewModel Form Validation (AUTH-06)

    @MainActor
    func testAuthenticationViewModelValidation() {
        let vm = AuthenticationViewModel()

        // Empty state
        XCTAssertFalse(vm.isLoginFormValid)
        XCTAssertFalse(vm.isRegisterFormValid)

        // Invalid email
        vm.email = "notanemail"
        vm.password = "123456"
        XCTAssertFalse(vm.isEmailValid)
        XCTAssertFalse(vm.isLoginFormValid)

        // Valid email, valid password for login
        vm.email = "user@example.com"
        XCTAssertTrue(vm.isEmailValid)
        XCTAssertTrue(vm.isPasswordValid)
        XCTAssertTrue(vm.isLoginFormValid)

        // Short password for registration (< 6 chars)
        vm.password = "12345"
        vm.confirmPassword = "12345"
        XCTAssertFalse(vm.isPasswordValid)
        XCTAssertFalse(vm.isRegisterFormValid)

        // Mismatched confirm password
        vm.password = "123456"
        vm.confirmPassword = "mismatch"
        XCTAssertFalse(vm.doPasswordsMatch)
        XCTAssertFalse(vm.isRegisterFormValid)

        // Valid registration
        vm.confirmPassword = "123456"
        XCTAssertTrue(vm.doPasswordsMatch)
        XCTAssertTrue(vm.isRegisterFormValid)

        // Mode toggling
        vm.isRegisterMode = false
        vm.toggleMode()
        XCTAssertTrue(vm.isRegisterMode)
        vm.toggleMode()
        XCTAssertFalse(vm.isRegisterMode)
    }
}
