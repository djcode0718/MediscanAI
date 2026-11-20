import Foundation
import os

// MARK: - Auth Manager (AUTH-02, AUTH-03, AUTH-04, AUTH-05)

/// Observable central authentication state manager for the native iOS application.
/// Coordinates session restoration, credentials persistence in Keychain, login,
/// registration, logout, and automatic session revocation upon 401 interception.
@Observable
public final class AuthManager {
    public private(set) var state: AuthState = .unauthenticated
    public private(set) var isRestoringSession: Bool = false

    public let networkClient: NetworkClientProtocol
    public let keychain: KeychainStorageProtocol
    public let authProvider: AuthorizationHeaderProviding

    private let logger = Logger(subsystem: "ai.mediscan.ios", category: "AuthManager")

    // MARK: - Computed Properties

    public var currentUser: UserResponse? {
        if case .authenticated(let session) = state {
            return session.user
        }
        return nil
    }

    public var isAuthenticated: Bool {
        if case .authenticated = state {
            return true
        }
        return false
    }

    // MARK: - Initialization

    public init(
        networkClient: NetworkClientProtocol,
        keychain: KeychainStorageProtocol = KeychainStorage(),
        authProvider: AuthorizationHeaderProviding = InMemoryAuthorizationHeaderProvider()
    ) {
        self.networkClient = networkClient
        self.keychain = keychain
        self.authProvider = authProvider
    }

    // MARK: - Session Restoration (AUTH-05)

    /// Restores a persisted session from the Secure Enclave / Keychain on application launch.
    /// If a token is found, verifies validity against `GET /api/auth/me`.
    /// On 401 Unauthorized, automatically wipes invalid token from Keychain.
    @MainActor
    public func restoreSession() async {
        isRestoringSession = true
        defer { isRestoringSession = false }

        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-UITest_AuthenticatedUser") {
            let testUser = UserResponse(
                id: 1,
                email: "clinician@mediscan.ai",
                fullName: "Dr. Jane Foster",
                isActive: true,
                isSuperuser: false,
                createdAt: Date()
            )
            let testSession = UserSession(token: "uitest_mock_jwt_token", user: testUser)
            authProvider.setToken("uitest_mock_jwt_token")
            state = .authenticated(testSession)
            return
        }
        #endif

        logger.debug("Beginning session restoration check...")

        guard let token = try? keychain.getToken(), !token.isEmpty else {
            logger.debug("No persisted token found in Keychain.")
            authProvider.setToken(nil)
            state = .unauthenticated
            return
        }

        // Set token in header provider to authorize /api/auth/me
        authProvider.setToken(token)

        do {
            let user = try await networkClient.send(endpoint: .authMe, responseType: UserResponse.self)
            let session = UserSession(token: token, user: user)
            state = .authenticated(session)
            logger.info("Session successfully restored for user id=\(user.id, privacy: .public)")
        } catch let apiError as APIError {
            logger.warning("Session restoration failed: \(apiError.localizedDescription, privacy: .public)")
            switch apiError {
            case .unauthorized:
                // Token is expired, invalid, or revoked -> delete from Keychain
                try? keychain.deleteToken()
                authProvider.setToken(nil)
                state = .unauthenticated
            default:
                // Network or other connectivity error: clear in-memory auth for safety, keep keychain for retry
                authProvider.setToken(nil)
                state = .unauthenticated
            }
        } catch {
            logger.error("Unexpected error during session restoration: \(error.localizedDescription, privacy: .public)")
            authProvider.setToken(nil)
            state = .unauthenticated
        }
    }

    // MARK: - User Registration (AUTH-03)

    /// Register a new user account with `POST /api/auth/register`.
    /// On success, persists token in Keychain, configures auth header, and transitions to `.authenticated`.
    @MainActor
    @discardableResult
    public func register(
        email: String,
        password: String,
        fullName: String? = nil
    ) async throws -> UserResponse {
        state = .authenticating

        let normalizedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let trimmedName = fullName?.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolvedName = (trimmedName?.isEmpty == false) ? trimmedName : nil

        let request = UserRegisterRequest(
            email: normalizedEmail,
            password: password,
            fullName: resolvedName
        )

        do {
            let response = try await networkClient.send(
                endpoint: .authRegister,
                body: request,
                responseType: TokenResponse.self
            )

            // Save token to Keychain
            try keychain.saveToken(response.accessToken)
            authProvider.setToken(response.accessToken)

            let session = UserSession(token: response.accessToken, user: response.user)
            state = .authenticated(session)
            logger.info("User registered successfully: id=\(response.user.id, privacy: .public)")
            return response.user
        } catch {
            authProvider.setToken(nil)
            state = .unauthenticated
            logger.error("Registration failed: \(error.localizedDescription, privacy: .public)")
            throw error
        }
    }

    // MARK: - User Login (AUTH-04)

    /// Authenticate credentials against `POST /api/auth/login`.
    /// On success, securely saves token to Keychain and updates session state.
    @MainActor
    @discardableResult
    public func login(
        email: String,
        password: String
    ) async throws -> UserResponse {
        state = .authenticating

        let normalizedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let request = UserLoginRequest(email: normalizedEmail, password: password)

        do {
            let response = try await networkClient.send(
                endpoint: .authLogin,
                body: request,
                responseType: TokenResponse.self
            )

            // Save token to Keychain
            try keychain.saveToken(response.accessToken)
            authProvider.setToken(response.accessToken)

            let session = UserSession(token: response.accessToken, user: response.user)
            state = .authenticated(session)
            logger.info("User logged in successfully: id=\(response.user.id, privacy: .public)")
            return response.user
        } catch {
            authProvider.setToken(nil)
            state = .unauthenticated
            logger.error("Login failed: \(error.localizedDescription, privacy: .public)")
            throw error
        }
    }

    // MARK: - User Logout

    /// Explicitly terminates active session, clears Keychain, and resets auth headers.
    @MainActor
    public func logout() {
        logger.info("Logging out current user session...")
        try? keychain.deleteToken()
        authProvider.setToken(nil)
        state = .unauthenticated
    }

    // MARK: - Automatic 401 Interception (AUTH-05)

    /// Called by the NetworkClient when a protected endpoint returns HTTP 401 Unauthorized.
    /// Wipes stored credentials and resets state without causing duplicate storm triggers.
    @MainActor
    public func handleUnauthorized() {
        guard isAuthenticated else { return }

        logger.warning("Handling unauthorized 401 event. Revoking local session...")
        try? keychain.deleteToken()
        authProvider.setToken(nil)
        state = .unauthenticated
    }
}
