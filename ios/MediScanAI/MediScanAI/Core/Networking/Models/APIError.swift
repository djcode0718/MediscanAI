import Foundation

// MARK: - Backend Error Payload (FastAPI HTTPException format)

public struct BackendErrorPayload: Codable, Equatable {
    public let detail: String?

    public init(detail: String?) {
        self.detail = detail
    }
}

// MARK: - Strongly Typed API Error (NET-06)

public enum APIError: Error, Equatable, LocalizedError {
    case invalidURL
    case noConnection
    case timeout
    case badRequest(detail: String?)
    case unauthorized(detail: String?)
    case forbidden(detail: String?)
    case notFound(detail: String?)
    case unprocessableEntity(detail: String?)
    case rateLimited(retryAfter: Int?, detail: String?)
    case serviceUnavailable(retryAfter: Int?, detail: String?)
    case serverError(statusCode: Int, detail: String?)
    case invalidResponse
    case decodingError(message: String)
    case cancelled
    case unknown(message: String)

    public var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid target server URL."
        case .noConnection:
            return "No network connection. Please check your Wi-Fi or cellular network."
        case .timeout:
            return "The request timed out. Please try again."
        case .badRequest(let detail):
            return detail ?? "Invalid request parameters."
        case .unauthorized(let detail):
            return detail ?? "Authentication required. Please sign in."
        case .forbidden(let detail):
            return detail ?? "You do not have permission to perform this action."
        case .notFound(let detail):
            return detail ?? "The requested resource was not found."
        case .unprocessableEntity(let detail):
            return detail ?? "Validation error. Please verify input data."
        case .rateLimited(let retryAfter, let detail):
            if let seconds = retryAfter {
                return detail ?? "Rate limit exceeded. Please wait \(seconds) seconds."
            }
            return detail ?? "Rate limit exceeded. Please wait before retrying."
        case .serviceUnavailable(let retryAfter, let detail):
            if let seconds = retryAfter {
                return detail ?? "Server temporarily busy. Please retry in \(seconds) seconds."
            }
            return detail ?? "Server unavailable. Processing components initializing."
        case .serverError(let code, let detail):
            return detail ?? "Server error (\(code)). Please try again later."
        case .invalidResponse:
            return "Received an invalid or malformed response from the server."
        case .decodingError(let message):
            return "Failed to process server response: \(message)"
        case .cancelled:
            return "The request was cancelled."
        case .unknown(let message):
            return message
        }
    }

    // MARK: - Factory from HTTP Status Code & Raw Response Data
    public static func from(
        statusCode: Int,
        data: Data?,
        httpResponse: HTTPURLResponse?
    ) -> APIError {
        var detail: String?
        if let data = data, !data.isEmpty {
            if let parsed = try? JSONDecoder().decode(BackendErrorPayload.self, from: data) {
                detail = parsed.detail
            } else if let rawString = String(data: data, encoding: .utf8), !rawString.isEmpty {
                // If detail is not a JSON object, read plain string up to 200 chars
                detail = String(rawString.prefix(200))
            }
        }

        // Parse Retry-After header if present
        let retryAfter: Int? = {
            guard let retryHeader = httpResponse?.value(forHTTPHeaderField: "Retry-After") else {
                return nil
            }
            return Int(retryHeader.trimmingCharacters(in: .whitespaces))
        }()

        switch statusCode {
        case 400:
            return .badRequest(detail: detail)
        case 401:
            return .unauthorized(detail: detail)
        case 403:
            return .forbidden(detail: detail)
        case 404:
            return .notFound(detail: detail)
        case 422:
            return .unprocessableEntity(detail: detail)
        case 429:
            return .rateLimited(retryAfter: retryAfter, detail: detail)
        case 503:
            return .serviceUnavailable(retryAfter: retryAfter, detail: detail)
        case 500...599:
            return .serverError(statusCode: statusCode, detail: detail)
        default:
            return .unknown(message: detail ?? "HTTP Error \(statusCode)")
        }
    }
}
