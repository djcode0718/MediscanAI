import Foundation

// MARK: - Authorization Header Provider Protocol

public protocol AuthorizationHeaderProviding: AnyObject {
    /// Retrieve current bearer token if set
    var currentToken: String? { get }

    /// Update or replace bearer token in memory
    func setToken(_ token: String?)

    /// Return HTTP authorization header value (e.g. "Bearer <token>") or nil
    func authorizationHeaderValue() -> String?

    /// Safe redacted token representation for logging (e.g. "Bearer eyJh...wxyz")
    func redactedAuthorizationHeader() -> String?
}

// MARK: - In-Memory Authorization Header Provider

public final class InMemoryAuthorizationHeaderProvider: AuthorizationHeaderProviding {
    private let lock = NSLock()
    private var token: String?

    public init(initialToken: String? = nil) {
        self.token = initialToken
    }

    public var currentToken: String? {
        lock.lock()
        defer { lock.unlock() }
        return token
    }

    public func setToken(_ token: String?) {
        lock.lock()
        defer { lock.unlock() }
        self.token = token
    }

    public func authorizationHeaderValue() -> String? {
        lock.lock()
        defer { lock.unlock() }
        guard let token = token, !token.isEmpty else { return nil }
        return "Bearer \(token)"
    }

    public func redactedAuthorizationHeader() -> String? {
        lock.lock()
        defer { lock.unlock() }
        guard let token = token, !token.isEmpty else { return nil }
        if token.count > 10 {
            let prefix = token.prefix(4)
            let suffix = token.suffix(4)
            return "Bearer \(prefix)...\(suffix)"
        }
        return "Bearer ***"
    }
}
