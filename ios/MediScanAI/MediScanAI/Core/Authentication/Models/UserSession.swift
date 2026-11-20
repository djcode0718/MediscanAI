import Foundation

// MARK: - User Session (AUTH-02)

/// Represents an active, authenticated user session containing the secure JWT
/// and the verified user profile.
public struct UserSession: Equatable, Codable {
    public let token: String
    public let user: UserResponse

    public init(token: String, user: UserResponse) {
        self.token = token
        self.user = user
    }
}

// MARK: - Authentication State (AUTH-02)

/// Explicit state machine representing current authentication lifecycle.
public enum AuthState: Equatable {
    /// No authenticated user; unauthenticated public flow
    case unauthenticated

    /// Ongoing network authentication or registration attempt
    case authenticating

    /// Valid authenticated session active with token and profile
    case authenticated(UserSession)
}
