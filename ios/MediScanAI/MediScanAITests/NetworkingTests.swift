import XCTest
import Foundation
@testable import MediScanAI

// MARK: - Mock Network Transport

final class MockNetworkTransport: NetworkTransport {
    var handler: ((URLRequest) throws -> (Data, HTTPURLResponse))?
    private(set) var recordedRequests: [URLRequest] = []

    func execute(request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        recordedRequests.append(request)
        guard let handler = handler else {
            let errorResponse = HTTPURLResponse(
                url: request.url ?? URL(string: "http://localhost")!,
                statusCode: 500,
                httpVersion: nil,
                headerFields: nil
            )!
            return (Data(), errorResponse)
        }
        return try handler(request)
    }
}

// MARK: - Networking Tests Suite

final class NetworkingTests: XCTestCase {

    // MARK: - 1. Configuration & APIEnvironment Tests (NET-02)

    func testNetworkConfigurationNormalizationAndDefaults() {
        let testDefaults = UserDefaults(suiteName: "NetworkingTestsSuite")!
        testDefaults.removePersistentDomain(forName: "NetworkingTestsSuite")

        let config = NetworkConfiguration(defaults: testDefaults)
        XCTAssertEqual(config.baseURL.absoluteString, "http://192.168.0.155:8000")

        // Update with trailing slash - should normalize
        let updated = config.updateBaseURL(from: "http://192.168.1.100:8000///")
        XCTAssertTrue(updated)
        XCTAssertEqual(config.baseURL.absoluteString, "http://192.168.1.100:8000")

        // Invalid URL should fail validation
        let invalid = config.updateBaseURL(from: "ftp://invalid-url")
        XCTAssertFalse(invalid)
        XCTAssertEqual(config.baseURL.absoluteString, "http://192.168.1.100:8000")

        // Reset to default
        config.resetToDefault()
        XCTAssertEqual(config.baseURL.absoluteString, "http://192.168.0.155:8000")
    }

    func testAPIEnvironmentSecureDetection() {
        let dev = APIEnvironment.development(baseURL: URL(string: "http://192.168.0.155:8000")!)
        XCTAssertFalse(dev.isSecure)

        let prod = APIEnvironment.production(baseURL: URL(string: "https://api.mediscan.ai")!)
        XCTAssertTrue(prod.isSecure)
    }

    // MARK: - 2. API Endpoint Taxonomy Tests (NET-01)

    func testAPIEndpointTaxonomyAndURLs() {
        let baseURL = URL(string: "http://192.168.0.155:8000")!

        // Health
        let health = APIEndpoint.health
        XCTAssertEqual(health.method, .get)
        XCTAssertEqual(health.path, "/api/health")
        XCTAssertFalse(health.requiresAuthorization)
        XCTAssertEqual(health.timeoutInterval, 15.0)
        XCTAssertEqual(health.url(relativeTo: baseURL)?.absoluteString, "http://192.168.0.155:8000/api/health")

        // Ready
        let ready = APIEndpoint.ready
        XCTAssertEqual(ready.method, .get)
        XCTAssertEqual(ready.path, "/api/ready")
        XCTAssertFalse(ready.requiresAuthorization)

        // Auth
        let register = APIEndpoint.authRegister
        XCTAssertEqual(register.method, .post)
        XCTAssertEqual(register.path, "/api/auth/register")
        XCTAssertFalse(register.requiresAuthorization)

        let login = APIEndpoint.authLogin
        XCTAssertEqual(login.method, .post)
        XCTAssertEqual(login.path, "/api/auth/login")
        XCTAssertFalse(login.requiresAuthorization)

        let me = APIEndpoint.authMe
        XCTAssertEqual(me.method, .get)
        XCTAssertEqual(me.path, "/api/auth/me")
        XCTAssertTrue(me.requiresAuthorization)

        // Analyze (NET-07)
        let analyze = APIEndpoint.analyze
        XCTAssertEqual(analyze.method, .post)
        XCTAssertEqual(analyze.path, "/api/analyze")
        XCTAssertTrue(analyze.requiresAuthorization)
        XCTAssertEqual(analyze.timeoutInterval, 120.0)

        // Analyses History & Management
        let list = APIEndpoint.analysesList(limit: 15, offset: 30)
        XCTAssertEqual(list.method, .get)
        XCTAssertTrue(list.requiresAuthorization)
        let listURL = list.url(relativeTo: baseURL)?.absoluteString ?? ""
        XCTAssertTrue(listURL.contains("limit=15"))
        XCTAssertTrue(listURL.contains("offset=30"))

        let detail = APIEndpoint.analysisDetail(id: 42)
        XCTAssertEqual(detail.method, .get)
        XCTAssertEqual(detail.path, "/api/analyses/42")
        XCTAssertTrue(detail.requiresAuthorization)

        let delete = APIEndpoint.analysisDelete(id: 42)
        XCTAssertEqual(delete.method, .delete)
        XCTAssertEqual(delete.path, "/api/analyses/42")
        XCTAssertTrue(delete.requiresAuthorization)
    }

    // MARK: - 3. Authorization Header & Redaction Tests

    func testAuthorizationHeaderProvider() {
        let provider = InMemoryAuthorizationHeaderProvider()
        XCTAssertNil(provider.authorizationHeaderValue())
        XCTAssertNil(provider.redactedAuthorizationHeader())

        provider.setToken("eyJhYmMxMjM0NTY3ODkw.jwtTokenPayload.signatureXYZ987")
        XCTAssertEqual(provider.authorizationHeaderValue(), "Bearer eyJhYmMxMjM0NTY3ODkw.jwtTokenPayload.signatureXYZ987")
        XCTAssertEqual(provider.redactedAuthorizationHeader(), "Bearer eyJh...Z987")

        // Replacement
        provider.setToken("shortToken")
        XCTAssertEqual(provider.redactedAuthorizationHeader(), "Bearer ***")

        // Clear
        provider.setToken(nil)
        XCTAssertNil(provider.authorizationHeaderValue())
    }

    func testNetworkClientEnforcesAuthorizationWhenRequired() async {
        let transport = MockNetworkTransport()
        let authProvider = InMemoryAuthorizationHeaderProvider(initialToken: nil) // No token set
        let client = NetworkClient(
            configuration: NetworkConfiguration(),
            transport: transport,
            authProvider: authProvider
        )

        // Protected endpoint without token should immediately throw unauthorized
        do {
            let _: UserResponse = try await client.send(endpoint: .authMe, responseType: UserResponse.self)
            XCTFail("Should have thrown unauthorized error due to missing token")
        } catch let error as APIError {
            if case .unauthorized(let detail) = error {
                XCTAssertEqual(detail, "Missing bearer authentication token.")
            } else {
                XCTFail("Expected unauthorized error, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error type: \(error)")
        }
    }

    // MARK: - 4. Correlation ID Injection (NET-05)

    func testCorrelationIDHeaderInjection() async throws {
        let transport = MockNetworkTransport()
        transport.handler = { request in
            let header = request.value(forHTTPHeaderField: "X-Request-ID")
            XCTAssertNotNil(header)
            XCTAssertFalse(header!.isEmpty)

            let json = """
            {"status": "alive", "app": "MediScanAI", "environment": "development", "timestamp": 1700000000.0}
            """.data(using: .utf8)!

            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["X-Request-ID": header!]
            )!
            return (json, response)
        }

        let client = NetworkClient(transport: transport)
        let health: HealthCheckResponse = try await client.send(endpoint: .health, responseType: HealthCheckResponse.self)
        XCTAssertEqual(health.status, "alive")
        XCTAssertEqual(transport.recordedRequests.count, 1)
    }

    // MARK: - 5. Error Mapping Tests (NET-06)

    func testErrorMappingFromStatusCodes() async {
        let testCases: [(code: Int, payload: String, headers: [String: String]?, assertion: (APIError) -> Bool)] = [
            (
                400,
                "{\"detail\": \"At least symptom text, recorded audio, or a medicine image must be provided.\"}",
                nil,
                { if case .badRequest(let d) = $0 { return d?.contains("symptom text") == true }; return false }
            ),
            (
                401,
                "{\"detail\": \"Invalid email or password\"}",
                nil,
                { if case .unauthorized(let d) = $0 { return d == "Invalid email or password" }; return false }
            ),
            (
                403,
                "{\"detail\": \"Forbidden\"}",
                nil,
                { if case .forbidden = $0 { return true }; return false }
            ),
            (
                404,
                "{\"detail\": \"Analysis record not found.\"}",
                nil,
                { if case .notFound(let d) = $0 { return d == "Analysis record not found." }; return false }
            ),
            (
                422,
                "{\"detail\": \"Unprocessable entity\"}",
                nil,
                { if case .unprocessableEntity = $0 { return true }; return false }
            ),
            (
                429,
                "{\"detail\": \"Rate limit exceeded.\"}",
                ["Retry-After": "30"],
                { if case .rateLimited(let retry, _) = $0 { return retry == 30 }; return false }
            ),
            (
                503,
                "{\"detail\": \"Maximum concurrent clinical analyses active.\"}",
                ["Retry-After": "5"],
                { if case .serviceUnavailable(let retry, let d) = $0 { return retry == 5 && d?.contains("concurrent") == true }; return false }
            ),
            (
                500,
                "{\"detail\": \"Internal pipeline crash.\"}",
                nil,
                { if case .serverError(let code, _) = $0 { return code == 500 }; return false }
            )
        ]

        for (code, payload, headers, assertMatch) in testCases {
            let transport = MockNetworkTransport()
            transport.handler = { request in
                let response = HTTPURLResponse(
                    url: request.url!,
                    statusCode: code,
                    httpVersion: nil,
                    headerFields: headers
                )!
                return (payload.data(using: .utf8)!, response)
            }

            let client = NetworkClient(transport: transport)
            do {
                let _: HealthCheckResponse = try await client.send(endpoint: .health, responseType: HealthCheckResponse.self)
                XCTFail("Should have thrown error for HTTP \(code)")
            } catch let apiError as APIError {
                XCTAssertTrue(assertMatch(apiError), "Failed asserting error pattern for code \(code): \(apiError)")
            } catch {
                XCTFail("Unexpected error type: \(error)")
            }
        }
    }

    // MARK: - 6. Model Decoding Pipeline (NET-03)

    func testUserResponseAndTokenResponseDecoding() throws {
        let json = """
        {
            "access_token": "mock.jwt.token",
            "token_type": "bearer",
            "user": {
                "id": 7,
                "email": "doctor@mediscan.ai",
                "full_name": "Dr. Sarah Adams",
                "is_active": true,
                "is_superuser": false,
                "created_at": "2026-11-18T08:30:00.000000Z"
            }
        }
        """.data(using: .utf8)!

        let decoder = NetworkClient.makeDefaultDecoder()
        let tokenResponse = try decoder.decode(TokenResponse.self, from: json)

        XCTAssertEqual(tokenResponse.accessToken, "mock.jwt.token")
        XCTAssertEqual(tokenResponse.tokenType, "bearer")
        XCTAssertEqual(tokenResponse.user.id, 7)
        XCTAssertEqual(tokenResponse.user.email, "doctor@mediscan.ai")
        XCTAssertEqual(tokenResponse.user.fullName, "Dr. Sarah Adams")
        XCTAssertTrue(tokenResponse.user.isActive)
        XCTAssertFalse(tokenResponse.user.isSuperuser)
    }

    func testAnalysisResultResponseDecoding() throws {
        let json = """
        {
            "analysis_id": 42,
            "timings": {
                "whisper_ms": 140,
                "ocr_total_ms": 320,
                "total_duration_ms": 1850
            },
            "meta": {
                "mismatch": null,
                "mismatch_details": "Packaging verified",
                "ocr_status": "SUCCESS",
                "fast_path": false
            },
            "card": {
                "user_text": "Severe headache",
                "ocr_text": "PARACETAMOL 500MG TABLETS",
                "llm_output": "### Clinical Assessment\\nParacetamol is indicated for tension headaches.",
                "retrieved": {
                    "diseases": [
                        {
                            "key": "D001",
                            "score": 0.892,
                            "preview": {"disease": "Tension Headache", "symptoms": "Bilateral mild to moderate ache"}
                        }
                    ],
                    "drugs": [
                        {
                            "key": "DRUG-01",
                            "score": 0.945,
                            "preview": {"generic_name": "Acetaminophen", "brand_name": "Tylenol"}
                        }
                    ],
                    "drug_dict": []
                }
            }
        }
        """.data(using: .utf8)!

        let decoder = NetworkClient.makeDefaultDecoder()
        let analysis = try decoder.decode(AnalysisResultResponse.self, from: json)

        XCTAssertEqual(analysis.analysisId, 42)
        XCTAssertEqual(analysis.timings?["whisper_ms"], 140)
        XCTAssertEqual(analysis.meta?.ocrStatus, "SUCCESS")
        XCTAssertEqual(analysis.card.ocrText, "PARACETAMOL 500MG TABLETS")
        XCTAssertEqual(analysis.card.retrieved?.diseases?.count, 1)
        XCTAssertEqual(analysis.card.retrieved?.diseases?.first?.key, "D001")
        XCTAssertEqual(analysis.card.retrieved?.drugs?.count, 1)
    }

    // MARK: - 7. Multipart Form-Data Encoder Tests (NET-04)

    func testMultipartFormDataEncoderEncodingAndValidation() throws {
        let encoder = MultipartFormDataEncoder(boundary: "STATIC-TEST-BOUNDARY")

        // 1. Validation: Empty submission rejected
        XCTAssertThrowsError(try encoder.encode(payload: AnalysisUploadPayload())) { error in
            XCTAssertEqual(error as? MultipartFormDataEncoder.ValidationError, .emptySubmission)
        }

        // 2. Validation: Text exceeds limit (4,000 chars)
        let longText = String(repeating: "A", count: 4001)
        XCTAssertThrowsError(try encoder.encode(payload: AnalysisUploadPayload(text: longText))) { error in
            if case .textExceedsLimit(let count, let limit) = error as? MultipartFormDataEncoder.ValidationError {
                XCTAssertEqual(count, 4001)
                XCTAssertEqual(limit, 4000)
            } else {
                XCTFail("Expected textExceedsLimit error")
            }
        }

        // 3. Validation: Image exceeds limit (10MB)
        let oversizedImage = MultipartFileItem(
            fieldName: "image",
            filename: "photo.jpg",
            mimeType: "image/jpeg",
            data: Data(repeating: 0xFF, count: 10 * 1024 * 1024 + 1)
        )
        XCTAssertThrowsError(try encoder.encode(payload: AnalysisUploadPayload(image: oversizedImage))) { error in
            if case .imageExceedsLimit = error as? MultipartFormDataEncoder.ValidationError {
                // Expected
            } else {
                XCTFail("Expected imageExceedsLimit error")
            }
        }

        // 4. Validation: Audio count exceeds limit (> 5 clips)
        let clips = (1...6).map {
            MultipartFileItem(fieldName: "audio", filename: "clip\($0).wav", mimeType: "audio/wav", data: Data([0x01, 0x02]))
        }
        XCTAssertThrowsError(try encoder.encode(payload: AnalysisUploadPayload(audioClips: clips))) { error in
            if case .audioCountExceedsLimit(let count, let limit) = error as? MultipartFormDataEncoder.ValidationError {
                XCTAssertEqual(count, 6)
                XCTAssertEqual(limit, 5)
            } else {
                XCTFail("Expected audioCountExceedsLimit error")
            }
        }

        // 5. Successful RFC 7578 Multipart Generation with Binary Data
        let sampleImageBytes = Data([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46]) // JPEG header
        let sampleAudioBytes = Data([0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00, 0x57, 0x41, 0x56, 0x45]) // WAV header

        let payload = AnalysisUploadPayload(
            text: "Patient reports chronic migraines.",
            image: MultipartFileItem(fieldName: "image", filename: "label.jpg", mimeType: "image/jpeg", data: sampleImageBytes),
            audioClips: [
                MultipartFileItem(fieldName: "audio", filename: "voice_symptoms.wav", mimeType: "audio/wav", data: sampleAudioBytes)
            ]
        )

        let (body, contentType) = try encoder.encode(payload: payload)

        XCTAssertEqual(contentType, "multipart/form-data; boundary=STATIC-TEST-BOUNDARY")
        let bodyString = String(decoding: body, as: UTF8.self)

        XCTAssertTrue(bodyString.contains("Content-Disposition: form-data; name=\"text\""))
        XCTAssertTrue(bodyString.contains("Patient reports chronic migraines."))
        XCTAssertTrue(bodyString.contains("Content-Disposition: form-data; name=\"image\"; filename=\"label.jpg\""))
        XCTAssertTrue(bodyString.contains("Content-Type: image/jpeg"))
        XCTAssertTrue(bodyString.contains("Content-Disposition: form-data; name=\"audio\"; filename=\"voice_symptoms.wav\""))
        XCTAssertTrue(bodyString.contains("Content-Type: audio/wav"))
        XCTAssertTrue(bodyString.hasSuffix("--STATIC-TEST-BOUNDARY--\r\n"))
    }

    // MARK: - 8. Health & Readiness Probe Methods (NET-08, NET-09)

    func testHealthProbeExecution() async throws {
        let transport = MockNetworkTransport()
        transport.handler = { request in
            let json = """
            {"status": "alive", "app": "MediScanAI", "environment": "development", "timestamp": 1729000000.0}
            """.data(using: .utf8)!
            let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            return (json, response)
        }

        let client = NetworkClient(transport: transport)
        let (health, latencyMs) = try await client.checkHealth()

        XCTAssertEqual(health.status, "alive")
        XCTAssertTrue(health.isAlive)
        XCTAssertGreaterThanOrEqual(latencyMs, 0.0)
    }

    func testReadinessProbeExecution() async throws {
        let transport = MockNetworkTransport()
        transport.handler = { request in
            let json = """
            {
                "status": "ready",
                "app": "MediScanAI",
                "environment": "development",
                "components": {
                    "database": "connected",
                    "models_loaded": "ready",
                    "ocr_prewarmed": "ready",
                    "ollama_service": "not_required"
                },
                "concurrency": {
                    "active_slots": 0,
                    "max_concurrent": 2
                },
                "startup_error": null
            }
            """.data(using: .utf8)!
            let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            return (json, response)
        }

        let client = NetworkClient(transport: transport)
        let readiness = try await client.checkReadiness()

        XCTAssertEqual(readiness.status, "ready")
        XCTAssertTrue(readiness.isReady)
        XCTAssertEqual(readiness.components.database, "connected")
        XCTAssertEqual(readiness.concurrency.maxConcurrent, 2)
    }

    // MARK: - 9. AppEnvironment Dependency Injection Test

    func testAppEnvironmentWithInjectedMockTransport() async throws {
        let mockTransport = MockNetworkTransport()
        mockTransport.handler = { request in
            let json = """
            {"status": "alive", "app": "MediScanAI", "environment": "development", "timestamp": 1700000000.0}
            """.data(using: .utf8)!
            return (json, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
        }

        let authProvider = InMemoryAuthorizationHeaderProvider()
        let config = NetworkConfiguration()
        let client = NetworkClient(configuration: config, transport: mockTransport, authProvider: authProvider)

        let env = AppEnvironment(
            networkConfiguration: config,
            authProvider: authProvider,
            networkClient: client
        )

        let (health, _) = try await env.networkClient.checkHealth()
        XCTAssertEqual(health.status, "alive")
        XCTAssertEqual(mockTransport.recordedRequests.count, 1)
    }
}
