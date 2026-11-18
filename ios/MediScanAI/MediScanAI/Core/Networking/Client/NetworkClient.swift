import Foundation
import os

// MARK: - Network Client Protocol

public protocol NetworkClientProtocol: AnyObject {
    var configuration: NetworkConfiguration { get }
    var authProvider: AuthorizationHeaderProviding { get }

    func send<T: Decodable>(endpoint: APIEndpoint, responseType: T.Type) async throws -> T
    func send<T: Decodable, Body: Encodable>(endpoint: APIEndpoint, body: Body, responseType: T.Type) async throws -> T
    func sendMultipart<T: Decodable>(endpoint: APIEndpoint, payload: AnalysisUploadPayload, responseType: T.Type) async throws -> T
    func checkHealth() async throws -> (response: HealthCheckResponse, latencyMs: Double)
    func checkReadiness() async throws -> ReadinessResponse
}

// MARK: - Native Network Client Implementation

public final class NetworkClient: NetworkClientProtocol {
    public let configuration: NetworkConfiguration
    public let transport: NetworkTransport
    public let authProvider: AuthorizationHeaderProviding
    private let logger = Logger(subsystem: "ai.mediscan.ios", category: "NetworkClient")

    public static func makeDefaultDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let standardFormatter = ISO8601DateFormatter()
        standardFormatter.formatOptions = [.withInternetDateTime]

        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)

            if let date = formatter.date(from: dateString) {
                return date
            }
            if let date = standardFormatter.date(from: dateString) {
                return date
            }
            // Fallback to Unix timestamp if numeric
            if let timestamp = Double(dateString) {
                return Date(timeIntervalSince1970: timestamp)
            }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date string '\(dateString)' into Date."
            )
        }
        return decoder
    }

    public static func makeDefaultEncoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }

    public init(
        configuration: NetworkConfiguration = NetworkConfiguration(),
        transport: NetworkTransport = URLSessionTransport(),
        authProvider: AuthorizationHeaderProviding = InMemoryAuthorizationHeaderProvider()
    ) {
        self.configuration = configuration
        self.transport = transport
        self.authProvider = authProvider
    }

    // MARK: - Standard GET / Parametric Requests

    public func send<T: Decodable>(
        endpoint: APIEndpoint,
        responseType: T.Type
    ) async throws -> T {
        try Task.checkCancellation()

        let request = try buildRequest(endpoint: endpoint, httpBody: nil, contentType: "application/json")
        return try await executeAndDecode(request: request, endpoint: endpoint, responseType: responseType)
    }

    // MARK: - JSON POST / Mutation Requests

    public func send<T: Decodable, Body: Encodable>(
        endpoint: APIEndpoint,
        body: Body,
        responseType: T.Type
    ) async throws -> T {
        try Task.checkCancellation()

        let encoder = Self.makeDefaultEncoder()
        let bodyData: Data
        do {
            bodyData = try encoder.encode(body)
        } catch {
            throw APIError.decodingError(message: "Failed to encode request body: \(error.localizedDescription)")
        }

        let request = try buildRequest(endpoint: endpoint, httpBody: bodyData, contentType: "application/json")
        return try await executeAndDecode(request: request, endpoint: endpoint, responseType: responseType)
    }

    // MARK: - Multipart Form-Data Requests (/api/analyze)

    public func sendMultipart<T: Decodable>(
        endpoint: APIEndpoint,
        payload: AnalysisUploadPayload,
        responseType: T.Type
    ) async throws -> T {
        try Task.checkCancellation()

        let encoder = MultipartFormDataEncoder()
        let (bodyData, contentType): (Data, String)
        do {
            (bodyData, contentType) = try encoder.encode(payload: payload)
        } catch let validationError as MultipartFormDataEncoder.ValidationError {
            throw APIError.badRequest(detail: validationError.localizedDescription)
        } catch {
            throw APIError.badRequest(detail: "Failed to encode multipart data: \(error.localizedDescription)")
        }

        let request = try buildRequest(endpoint: endpoint, httpBody: bodyData, contentType: contentType)
        return try await executeAndDecode(request: request, endpoint: endpoint, responseType: responseType)
    }

    // MARK: - Probes

    /// Check backend liveness and measure round-trip latency in milliseconds (NET-08)
    public func checkHealth() async throws -> (response: HealthCheckResponse, latencyMs: Double) {
        let startTime = CFAbsoluteTimeGetCurrent()
        let health: HealthCheckResponse = try await send(endpoint: .health, responseType: HealthCheckResponse.self)
        let latencyMs = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0
        return (health, latencyMs)
    }

    /// Check backend readiness metrics (database, models, OCR pre-warming, concurrency slots) (NET-09)
    public func checkReadiness() async throws -> ReadinessResponse {
        return try await send(endpoint: .ready, responseType: ReadinessResponse.self)
    }

    // MARK: - Request Builder

    private func buildRequest(
        endpoint: APIEndpoint,
        httpBody: Data?,
        contentType: String
    ) throws -> URLRequest {
        guard let url = endpoint.url(relativeTo: configuration.baseURL) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.timeoutInterval = endpoint.timeoutInterval
        request.httpBody = httpBody

        // 1. Content & Accept Headers
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // 2. Correlation ID Header (NET-05)
        let correlationId = UUID().uuidString
        request.setValue(correlationId, forHTTPHeaderField: "X-Request-ID")

        // 3. Authorization Header Injection
        if endpoint.requiresAuthorization {
            if let authHeader = authProvider.authorizationHeaderValue() {
                request.setValue(authHeader, forHTTPHeaderField: "Authorization")
            } else {
                // Endpoint strictly requires authentication, but no token is present
                throw APIError.unauthorized(detail: "Missing bearer authentication token.")
            }
        }

        return request
    }

    // MARK: - Execution & Decoding

    private func executeAndDecode<T: Decodable>(
        request: URLRequest,
        endpoint: APIEndpoint,
        responseType: T.Type
    ) async throws -> T {
        try Task.checkCancellation()

        let reqId = request.value(forHTTPHeaderField: "X-Request-ID") ?? "unknown"
        let method = request.httpMethod ?? "GET"
        let path = request.url?.path ?? ""

        logger.debug("Dispatching \(method, privacy: .public) \(path, privacy: .public) [X-Request-ID: \(reqId, privacy: .public)]")

        let data: Data
        let httpResponse: HTTPURLResponse
        do {
            (data, httpResponse) = try await transport.execute(request: request)
        } catch {
            if Task.isCancelled {
                throw APIError.cancelled
            }
            throw error
        }

        let statusCode = httpResponse.statusCode
        let responseReqId = httpResponse.value(forHTTPHeaderField: "X-Request-ID") ?? reqId

        logger.debug("Received HTTP \(statusCode, privacy: .public) for [X-Request-ID: \(responseReqId, privacy: .public)]")

        // Validate HTTP Status Code
        guard (200...299).contains(statusCode) else {
            throw APIError.from(statusCode: statusCode, data: data, httpResponse: httpResponse)
        }

        // Special case: if responseType is Void / Empty
        if responseType == EmptyResponse.self, let empty = EmptyResponse() as? T {
            return empty
        }

        // Decode JSON response
        let decoder = Self.makeDefaultDecoder()
        do {
            return try decoder.decode(T.self, from: data)
        } catch let decodingError as DecodingError {
            logger.error("JSON Decoding failure on \(path, privacy: .public): \(decodingError.localizedDescription, privacy: .public)")
            throw APIError.decodingError(message: decodingError.localizedDescription)
        } catch {
            throw APIError.decodingError(message: error.localizedDescription)
        }
    }
}

// MARK: - Empty Response Helper

public struct EmptyResponse: Codable, Equatable {
    public init() {}
}
