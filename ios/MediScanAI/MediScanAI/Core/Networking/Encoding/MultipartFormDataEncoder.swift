import Foundation

// MARK: - Multipart Upload Item Models

public struct MultipartFileItem: Equatable {
    public let fieldName: String
    public let filename: String
    public let mimeType: String
    public let data: Data

    public init(fieldName: String, filename: String, mimeType: String, data: Data) {
        self.fieldName = fieldName
        self.filename = filename
        self.mimeType = mimeType
        self.data = data
    }
}

public struct AnalysisUploadPayload: Equatable {
    public let text: String?
    public let image: MultipartFileItem?
    public let audioClips: [MultipartFileItem]

    public init(
        text: String? = nil,
        image: MultipartFileItem? = nil,
        audioClips: [MultipartFileItem] = []
    ) {
        self.text = text
        self.image = image
        self.audioClips = audioClips
    }
}

// MARK: - Multipart Form-Data Encoder (NET-04)

public final class MultipartFormDataEncoder {
    // Verified Backend Constraints from backend/core/config.py
    public static let maxTextLength = 4000
    public static let maxImageSizeBytes = 10 * 1024 * 1024 // 10 MB
    public static let maxAudioSizeBytes = 25 * 1024 * 1024 // 25 MB
    public static let maxAudioClipsCount = 5

    public enum ValidationError: Error, Equatable, LocalizedError {
        case emptySubmission
        case textExceedsLimit(count: Int, limit: Int)
        case imageExceedsLimit(size: Int, limit: Int)
        case audioExceedsLimit(filename: String, size: Int, limit: Int)
        case audioCountExceedsLimit(count: Int, limit: Int)

        public var errorDescription: String? {
            switch self {
            case .emptySubmission:
                return "At least symptom text, recorded audio, or a medicine image must be provided."
            case .textExceedsLimit(let count, let limit):
                return "Symptom text length (\(count)) exceeds maximum allowed limit of \(limit) characters."
            case .imageExceedsLimit(let size, let limit):
                return "Image file size (\(size / (1024 * 1024))MB) exceeds maximum limit of \(limit / (1024 * 1024))MB."
            case .audioExceedsLimit(let filename, let size, let limit):
                return "Audio clip '\(filename)' (\(size / (1024 * 1024))MB) exceeds maximum limit of \(limit / (1024 * 1024))MB."
            case .audioCountExceedsLimit(let count, let limit):
                return "Maximum allowed audio clips count is \(limit) (received \(count))."
            }
        }
    }

    public let boundary: String

    public init(boundary: String = "Boundary-\(UUID().uuidString)") {
        self.boundary = boundary
    }

    public var contentTypeHeader: String {
        "multipart/form-data; boundary=\(boundary)"
    }

    /// Encode an analysis payload with validation against backend constraints
    public func encode(payload: AnalysisUploadPayload) throws -> (data: Data, contentType: String) {
        // 1. Validation
        let hasText = payload.text != nil && !(payload.text?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true)
        let hasImage = payload.image != nil && !payload.image!.data.isEmpty
        let hasAudio = !payload.audioClips.isEmpty

        guard hasText || hasImage || hasAudio else {
            throw ValidationError.emptySubmission
        }

        if let text = payload.text, text.count > Self.maxTextLength {
            throw ValidationError.textExceedsLimit(count: text.count, limit: Self.maxTextLength)
        }

        if let image = payload.image, image.data.count > Self.maxImageSizeBytes {
            throw ValidationError.imageExceedsLimit(size: image.data.count, limit: Self.maxImageSizeBytes)
        }

        if payload.audioClips.count > Self.maxAudioClipsCount {
            throw ValidationError.audioCountExceedsLimit(count: payload.audioClips.count, limit: Self.maxAudioClipsCount)
        }

        for audio in payload.audioClips {
            if audio.data.count > Self.maxAudioSizeBytes {
                throw ValidationError.audioExceedsLimit(filename: audio.filename, size: audio.data.count, limit: Self.maxAudioSizeBytes)
            }
        }

        // 2. Build Multipart Body
        var body = Data()

        // Append text field
        if let text = payload.text, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            appendField(name: "text", value: text, to: &body)
        }

        // Append image field
        if let image = payload.image, !image.data.isEmpty {
            appendFile(
                fieldName: image.fieldName.isEmpty ? "image" : image.fieldName,
                filename: image.filename,
                mimeType: image.mimeType,
                fileData: image.data,
                to: &body
            )
        }

        // Append repeated audio fields (FastAPI expects repeated field name "audio")
        for audio in payload.audioClips {
            appendFile(
                fieldName: "audio",
                filename: audio.filename,
                mimeType: audio.mimeType,
                fileData: audio.data,
                to: &body
            )
        }

        // Closing boundary: --<boundary>--\r\n
        let closing = "--\(boundary)--\r\n"
        if let closingData = closing.data(using: .utf8) {
            body.append(closingData)
        }

        return (body, contentTypeHeader)
    }

    // MARK: - Internal Part Builders

    private func appendField(name: String, value: String, to body: inout Data) {
        var part = "--\(boundary)\r\n"
        part += "Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n"
        part += "\(value)\r\n"
        if let data = part.data(using: .utf8) {
            body.append(data)
        }
    }

    private func appendFile(
        fieldName: String,
        filename: String,
        mimeType: String,
        fileData: Data,
        to body: inout Data
    ) {
        var part = "--\(boundary)\r\n"
        part += "Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(filename)\"\r\n"
        part += "Content-Type: \(mimeType)\r\n\r\n"
        if let headerData = part.data(using: .utf8) {
            body.append(headerData)
            body.append(fileData)
            if let crlf = "\r\n".data(using: .utf8) {
                body.append(crlf)
            }
        }
    }
}
