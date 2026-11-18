import Foundation

// MARK: - API Environment

public enum APIEnvironment: Equatable {
    case development(baseURL: URL)
    case production(baseURL: URL)

    public static let defaultDevelopmentURL = URL(string: "http://192.168.0.155:8000")!

    public var baseURL: URL {
        switch self {
        case .development(let url):
            return url
        case .production(let url):
            return url
        }
    }

    public var isSecure: Bool {
        baseURL.scheme?.lowercased() == "https"
    }
}
