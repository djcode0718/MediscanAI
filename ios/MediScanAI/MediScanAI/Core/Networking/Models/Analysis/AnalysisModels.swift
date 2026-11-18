import Foundation

// MARK: - Retrieved Entity Item

public struct RetrievedItem: Codable, Equatable {
    public let key: String
    public let score: Double
    public let preview: [String: String]?

    public init(key: String, score: Double, preview: [String: String]? = nil) {
        self.key = key
        self.score = score
        self.preview = preview
    }
}

// MARK: - Retrieved Entities Container

public struct RetrievedEntities: Codable, Equatable {
    public let diseases: [RetrievedItem]?
    public let drugs: [RetrievedItem]?
    public let drugDict: [RetrievedItem]?

    public init(
        diseases: [RetrievedItem]? = nil,
        drugs: [RetrievedItem]? = nil,
        drugDict: [RetrievedItem]? = nil
    ) {
        self.diseases = diseases
        self.drugs = drugs
        self.drugDict = drugDict
    }

    private enum CodingKeys: String, CodingKey {
        case diseases
        case drugs
        case drugDict = "drug_dict"
    }
}

// MARK: - Analysis Summary Card

public struct AnalysisSummaryCard: Codable, Equatable {
    public let userText: String?
    public let ocrText: String?
    public let llmOutput: String?
    public let retrieved: RetrievedEntities?

    public init(
        userText: String? = nil,
        ocrText: String? = nil,
        llmOutput: String? = nil,
        retrieved: RetrievedEntities? = nil
    ) {
        self.userText = userText
        self.ocrText = ocrText
        self.llmOutput = llmOutput
        self.retrieved = retrieved
    }

    private enum CodingKeys: String, CodingKey {
        case userText = "user_text"
        case ocrText = "ocr_text"
        case llmOutput = "llm_output"
        case retrieved
    }
}

// MARK: - Analysis Metadata

public struct AnalysisMetadata: Codable, Equatable {
    public let mismatch: String?
    public let mismatchDetails: String?
    public let ocrStatus: String?
    public let fastPath: Bool?
    public let ocrErrorType: String?

    public init(
        mismatch: String? = nil,
        mismatchDetails: String? = nil,
        ocrStatus: String? = nil,
        fastPath: Bool? = nil,
        ocrErrorType: String? = nil
    ) {
        self.mismatch = mismatch
        self.mismatchDetails = mismatchDetails
        self.ocrStatus = ocrStatus
        self.fastPath = fastPath
        self.ocrErrorType = ocrErrorType
    }

    private enum CodingKeys: String, CodingKey {
        case mismatch
        case mismatchDetails = "mismatch_details"
        case ocrStatus = "ocr_status"
        case fastPath = "fast_path"
        case ocrErrorType = "ocr_error_type"
    }
}

// MARK: - Live Analysis Result Response (POST /api/analyze)

public struct AnalysisResultResponse: Codable, Equatable {
    public let card: AnalysisSummaryCard
    public let meta: AnalysisMetadata?
    public let analysisId: Int?
    public let timings: [String: Int]?

    public init(
        card: AnalysisSummaryCard,
        meta: AnalysisMetadata? = nil,
        analysisId: Int? = nil,
        timings: [String: Int]? = nil
    ) {
        self.card = card
        self.meta = meta
        self.analysisId = analysisId
        self.timings = timings
    }

    private enum CodingKeys: String, CodingKey {
        case card
        case meta
        case analysisId = "analysis_id"
        case timings
    }
}

// MARK: - Analysis List Item (GET /api/analyses item)

public struct AnalysisListItem: Codable, Equatable, Identifiable {
    public let id: Int
    public let modality: String
    public let status: String
    public let verdict: String?
    public let processingDurationMs: Int?
    public let createdAt: Date

    public init(
        id: Int,
        modality: String,
        status: String,
        verdict: String? = nil,
        processingDurationMs: Int? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.modality = modality
        self.status = status
        self.verdict = verdict
        self.processingDurationMs = processingDurationMs
        self.createdAt = createdAt
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case modality
        case status
        case verdict
        case processingDurationMs = "processing_duration_ms"
        case createdAt = "created_at"
    }
}

// MARK: - Paginated Analysis List Response (GET /api/analyses)

public struct AnalysisListResponse: Codable, Equatable {
    public let items: [AnalysisListItem]
    public let total: Int
    public let limit: Int
    public let offset: Int

    public init(items: [AnalysisListItem], total: Int, limit: Int, offset: Int) {
        self.items = items
        self.total = total
        self.limit = limit
        self.offset = offset
    }
}

// MARK: - Detailed Persisted Analysis Response (GET /api/analyses/{id})

public struct AnalysisDetailResponse: Codable, Equatable, Identifiable {
    public let id: Int
    public let userId: Int
    public let modality: String
    public let status: String
    public let verdict: String?
    public let summaryCard: AnalysisSummaryCard
    public let processingDurationMs: Int?
    public let createdAt: Date

    public init(
        id: Int,
        userId: Int,
        modality: String,
        status: String,
        verdict: String? = nil,
        summaryCard: AnalysisSummaryCard,
        processingDurationMs: Int? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.userId = userId
        self.modality = modality
        self.status = status
        self.verdict = verdict
        self.summaryCard = summaryCard
        self.processingDurationMs = processingDurationMs
        self.createdAt = createdAt
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case modality
        case status
        case verdict
        case summaryCard = "summary_card"
        case processingDurationMs = "processing_duration_ms"
        case createdAt = "created_at"
    }
}

// MARK: - Analysis Deletion Response (DELETE /api/analyses/{id})

public struct AnalysisDeleteResponse: Codable, Equatable {
    public let status: String
    public let id: Int

    public init(status: String = "deleted", id: Int) {
        self.status = status
        self.id = id
    }
}
