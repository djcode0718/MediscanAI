import Foundation

// MARK: - HTTP Method

public enum HTTPMethod: String, CustomStringConvertible {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case patch = "PATCH"
    case delete = "DELETE"

    public var description: String {
        rawValue
    }
}
