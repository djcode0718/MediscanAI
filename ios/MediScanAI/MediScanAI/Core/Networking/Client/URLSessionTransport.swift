import Foundation

// MARK: - Network Transport Protocol (for testability & mocking)

public protocol NetworkTransport: AnyObject {
    func execute(request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

// MARK: - Native URLSession Network Transport

public final class URLSessionTransport: NetworkTransport {
    private let session: URLSession

    public init(configuration: URLSessionConfiguration = .default) {
        // Enforce sensible resource limits and cache policies
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        self.session = URLSession(configuration: configuration)
    }

    public func execute(request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }
            return (data, httpResponse)
        } catch let error as APIError {
            throw error
        } catch let urlError as URLError {
            switch urlError.code {
            case .cancelled:
                throw APIError.cancelled
            case .timedOut:
                throw APIError.timeout
            case .notConnectedToInternet, .networkConnectionLost, .cannotConnectToHost:
                throw APIError.noConnection
            case .badURL, .unsupportedURL:
                throw APIError.invalidURL
            default:
                throw APIError.unknown(message: urlError.localizedDescription)
            }
        } catch {
            if Task.isCancelled {
                throw APIError.cancelled
            }
            throw APIError.unknown(message: error.localizedDescription)
        }
    }
}
