import Foundation

// MARK: - API Endpoint Definition (NET-01)

public enum APIEndpoint: Equatable {
    // Root & Health & Readiness Probes
    case root
    case health
    case ready

    // Authentication Endpoints
    case authRegister
    case authLogin
    case authMe

    // Multimodal Analysis Endpoint
    case analyze

    // Analysis History & Management Endpoints
    case analysesList(limit: Int = 20, offset: Int = 0)
    case analysisDetail(id: Int)
    case analysisDelete(id: Int)

    // MARK: - HTTP Method
    public var method: HTTPMethod {
        switch self {
        case .root, .health, .ready, .authMe, .analysesList, .analysisDetail:
            return .get
        case .authRegister, .authLogin, .analyze:
            return .post
        case .analysisDelete:
            return .delete
        }
    }

    // MARK: - Relative Path
    public var path: String {
        switch self {
        case .root:
            return "/"
        case .health:
            return "/api/health"
        case .ready:
            return "/api/ready"
        case .authRegister:
            return "/api/auth/register"
        case .authLogin:
            return "/api/auth/login"
        case .authMe:
            return "/api/auth/me"
        case .analyze:
            return "/api/analyze"
        case .analysesList:
            return "/api/analyses"
        case .analysisDetail(let id):
            return "/api/analyses/\(id)"
        case .analysisDelete(let id):
            return "/api/analyses/\(id)"
        }
    }

    // MARK: - Query Items
    public var queryItems: [URLQueryItem]? {
        switch self {
        case .analysesList(let limit, let offset):
            return [
                URLQueryItem(name: "limit", value: String(max(1, min(limit, 100)))),
                URLQueryItem(name: "offset", value: String(max(0, offset)))
            ]
        default:
            return nil
        }
    }

    // MARK: - Authentication Requirement
    public var requiresAuthorization: Bool {
        switch self {
        case .root, .health, .ready, .authRegister, .authLogin:
            return false
        case .authMe, .analyze, .analysesList, .analysisDetail, .analysisDelete:
            return true
        }
    }

    // MARK: - Request Timeout (NET-07)
    public var timeoutInterval: TimeInterval {
        switch self {
        case .analyze:
            return 120.0 // Heavy multimodal RAG inference pipeline
        default:
            return 15.0  // Standard request timeout
        }
    }

    // MARK: - URL Construction
    public func url(relativeTo baseURL: URL) -> URL? {
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: true)
        let normalizedPath = path.hasPrefix("/") ? path : "/\(path)"

        // Ensure clean path combining without double slashes
        if let currentPath = components?.path, !currentPath.isEmpty && currentPath != "/" {
            components?.path = currentPath.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + normalizedPath
        } else {
            components?.path = normalizedPath
        }

        if let queryItems = queryItems, !queryItems.isEmpty {
            components?.queryItems = queryItems
        }

        return components?.url
    }
}
