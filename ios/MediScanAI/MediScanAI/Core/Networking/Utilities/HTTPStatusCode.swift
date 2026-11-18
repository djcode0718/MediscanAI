import Foundation

// MARK: - HTTP Status Code

public enum HTTPStatusCode: Int, CustomStringConvertible {
    case ok = 200
    case created = 201
    case accepted = 202
    case noContent = 204
    
    case badRequest = 400
    case unauthorized = 401
    case forbidden = 403
    case notFound = 404
    case unprocessableEntity = 422
    case tooManyRequests = 429
    
    case internalServerError = 500
    case badGateway = 502
    case serviceUnavailable = 503
    case gatewayTimeout = 504

    public var isSuccess: Bool {
        (200...299).contains(rawValue)
    }

    public var isClientError: Bool {
        (400...499).contains(rawValue)
    }

    public var isServerError: Bool {
        (500...599).contains(rawValue)
    }

    public var description: String {
        "\(rawValue)"
    }
}
