import Foundation

// MARK: - Health Check Response (GET /api/health)

public struct HealthCheckResponse: Codable, Equatable {
    public let status: String
    public let app: String
    public let environment: String
    public let timestamp: Double

    public init(status: String = "alive", app: String = "MediScanAI", environment: String = "development", timestamp: Double = 0.0) {
        self.status = status
        self.app = app
        self.environment = environment
        self.timestamp = timestamp
    }

    public var isAlive: Bool {
        status.lowercased() == "alive" || status.lowercased() == "ok"
    }
}

// MARK: - Readiness Components

public struct ReadinessComponents: Codable, Equatable {
    public let database: String
    public let modelsLoaded: String
    public let ocrPrewarmed: String
    public let ollamaService: String

    public init(
        database: String = "connected",
        modelsLoaded: String = "ready",
        ocrPrewarmed: String = "ready",
        ollamaService: String = "not_required"
    ) {
        self.database = database
        self.modelsLoaded = modelsLoaded
        self.ocrPrewarmed = ocrPrewarmed
        self.ollamaService = ollamaService
    }

    private enum CodingKeys: String, CodingKey {
        case database
        case modelsLoaded = "models_loaded"
        case ocrPrewarmed = "ocr_prewarmed"
        case ollamaService = "ollama_service"
    }
}

// MARK: - Readiness Concurrency

public struct ReadinessConcurrency: Codable, Equatable {
    public let activeSlots: Int
    public let maxConcurrent: Int

    public init(activeSlots: Int = 0, maxConcurrent: Int = 2) {
        self.activeSlots = activeSlots
        self.maxConcurrent = maxConcurrent
    }

    private enum CodingKeys: String, CodingKey {
        case activeSlots = "active_slots"
        case maxConcurrent = "max_concurrent"
    }
}

// MARK: - Readiness Response (GET /api/ready)

public struct ReadinessResponse: Codable, Equatable {
    public let status: String
    public let app: String
    public let environment: String
    public let components: ReadinessComponents
    public let concurrency: ReadinessConcurrency
    public let startupError: String?

    public init(
        status: String = "ready",
        app: String = "MediScanAI",
        environment: String = "development",
        components: ReadinessComponents = ReadinessComponents(),
        concurrency: ReadinessConcurrency = ReadinessConcurrency(),
        startupError: String? = nil
    ) {
        self.status = status
        self.app = app
        self.environment = environment
        self.components = components
        self.concurrency = concurrency
        self.startupError = startupError
    }

    public var isReady: Bool {
        status.lowercased() == "ready"
    }

    private enum CodingKeys: String, CodingKey {
        case status
        case app
        case environment
        case components
        case concurrency
        case startupError = "startup_error"
    }
}
