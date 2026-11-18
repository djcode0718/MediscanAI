import Foundation
import SwiftUI
import os

// MARK: - Home View Model (NAV-02, NAV-04)

@Observable
@MainActor
public final class HomeViewModel {
    public private(set) var recentAnalyses: [AnalysisListItem] = []
    public private(set) var isLoading: Bool = false
    public private(set) var errorMessage: String? = nil

    public let networkClient: NetworkClientProtocol
    private let logger = Logger(subsystem: "ai.mediscan.ios", category: "HomeViewModel")

    public var isPopulated: Bool {
        !recentAnalyses.isEmpty
    }

    public var isEmpty: Bool {
        !isLoading && recentAnalyses.isEmpty && errorMessage == nil
    }

    public init(networkClient: NetworkClientProtocol) {
        self.networkClient = networkClient
    }

    // MARK: - Data Fetching

    /// Fetch the latest 3 analysis records for the authenticated user from GET /api/analyses.
    public func loadRecentActivity() async {
        guard !isLoading else { return }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await networkClient.send(
                endpoint: .analysesList(limit: 3, offset: 0),
                responseType: AnalysisListResponse.self
            )

            // Strictly enforce taking at most 3 items
            self.recentAnalyses = Array(response.items.prefix(3))
            self.isLoading = false
            logger.info("Loaded \(self.recentAnalyses.count, privacy: .public) recent analyses.")
        } catch let apiError as APIError {
            self.isLoading = false
            switch apiError {
            case .unauthorized:
                // Centralized 401 handling in NetworkClient will trigger session revocation
                self.errorMessage = "Session expired. Please sign in again."
            case .timeout:
                self.errorMessage = "Connection timed out loading recent activity."
            case .noConnection:
                self.errorMessage = "No network connection. Check device Wi-Fi."
            case .serverError(let code, _):
                self.errorMessage = "Server error (\(code)). Pull to retry."
            default:
                self.errorMessage = "Could not load recent activity: \(apiError.localizedDescription)"
            }
            logger.error("Failed to load recent activity: \(apiError.localizedDescription, privacy: .public)")
        } catch {
            self.isLoading = false
            self.errorMessage = "Could not load recent activity. Check local server connection."
            logger.error("Unexpected error loading recent activity: \(error.localizedDescription, privacy: .public)")
        }
    }

    // MARK: - Relative Timestamp Formatting

    nonisolated public static func relativeTimestamp(for date: Date, relativeTo now: Date = Date()) -> String {
        let interval = now.timeIntervalSince(date)
        if interval < 60 && interval >= 0 {
            return "Just now"
        }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: date, relativeTo: now)
    }
}
