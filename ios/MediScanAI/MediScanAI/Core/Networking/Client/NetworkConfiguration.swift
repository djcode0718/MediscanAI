import Foundation

// MARK: - Network Configuration Manager (NET-02)

public final class NetworkConfiguration {
    public static let defaultBaseURLString = "http://192.168.0.155:8000"
    private static let userDefaultsKey = "ai.mediscan.network.baseURL"

    private let defaults: UserDefaults
    private(set) public var baseURL: URL

    public init(defaults: UserDefaults = .standard, initialURL: URL? = nil) {
        self.defaults = defaults

        if let initial = initialURL {
            self.baseURL = Self.normalize(url: initial)
        } else if let savedString = defaults.string(forKey: Self.userDefaultsKey),
                  let savedURL = URL(string: savedString),
                  Self.isValid(url: savedURL) {
            self.baseURL = Self.normalize(url: savedURL)
        } else {
            self.baseURL = URL(string: Self.defaultBaseURLString)!
        }
    }

    /// Update the base URL and persist it to user defaults.
    /// Returns true if the URL was valid and applied; false otherwise.
    @discardableResult
    public func updateBaseURL(_ newURL: URL) -> Bool {
        guard Self.isValid(url: newURL) else { return false }
        let normalized = Self.normalize(url: newURL)
        self.baseURL = normalized
        defaults.set(normalized.absoluteString, forKey: Self.userDefaultsKey)
        return true
    }

    /// Update the base URL from a raw string.
    @discardableResult
    public func updateBaseURL(from string: String) -> Bool {
        let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed) else { return false }
        return updateBaseURL(url)
    }

    /// Reset configuration to default development URL.
    public func resetToDefault() {
        let defaultURL = URL(string: Self.defaultBaseURLString)!
        self.baseURL = defaultURL
        defaults.removeObject(forKey: Self.userDefaultsKey)
    }

    // MARK: - Validation & Normalization

    public static func isValid(url: URL) -> Bool {
        guard let scheme = url.scheme?.lowercased(), (scheme == "http" || scheme == "https") else {
            return false
        }
        guard let host = url.host, !host.isEmpty else {
            return false
        }
        return true
    }

    public static func normalize(url: URL) -> URL {
        var urlString = url.absoluteString
        while urlString.hasSuffix("/") {
            urlString.removeLast()
        }
        return URL(string: urlString) ?? url
    }
}
