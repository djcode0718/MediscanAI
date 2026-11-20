import Foundation

// MARK: - User Registration Request

public struct UserRegisterRequest: Codable, Equatable {
    public let email: String
    public let password: String
    public let fullName: String?

    public init(email: String, password: String, fullName: String? = nil) {
        self.email = email
        self.password = password
        self.fullName = fullName
    }

    private enum CodingKeys: String, CodingKey {
        case email
        case password
        case fullName = "full_name"
    }
}

// MARK: - User Login Request

public struct UserLoginRequest: Codable, Equatable {
    public let email: String
    public let password: String

    public init(email: String, password: String) {
        self.email = email
        self.password = password
    }
}

// MARK: - Safe User Response

public struct UserResponse: Codable, Equatable, Identifiable {
    public let id: Int
    public let email: String
    public let fullName: String?
    public let isActive: Bool
    public let isSuperuser: Bool
    public let createdAt: Date

    public init(
        id: Int,
        email: String,
        fullName: String? = nil,
        isActive: Bool = true,
        isSuperuser: Bool = false,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.email = email
        self.fullName = fullName
        self.isActive = isActive
        self.isSuperuser = isSuperuser
        self.createdAt = createdAt
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case email
        case fullName = "full_name"
        case isActive = "is_active"
        case isSuperuser = "is_superuser"
        case createdAt = "created_at"
    }
}

// MARK: - Token Response

public struct TokenResponse: Codable, Equatable {
    public let accessToken: String
    public let tokenType: String
    public let user: UserResponse

    public init(accessToken: String, tokenType: String = "bearer", user: UserResponse) {
        self.accessToken = accessToken
        self.tokenType = tokenType
        self.user = user
    }

    private enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case user
    }
}
