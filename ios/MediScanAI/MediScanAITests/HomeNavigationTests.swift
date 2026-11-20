import XCTest
import Foundation
@testable import MediScanAI

// MARK: - Home Navigation Unit Tests (NAV-01 through NAV-04)

final class HomeNavigationTests: XCTestCase {

    private var mockTransport: MockNetworkTransport!
    private var networkClient: NetworkClient!

    override func setUp() {
        super.setUp()
        mockTransport = MockNetworkTransport()
        let authProvider = InMemoryAuthorizationHeaderProvider()
        authProvider.setToken("mock_test_token_12345")
        networkClient = NetworkClient(
            transport: mockTransport,
            authProvider: authProvider
        )
    }

    override func tearDown() {
        mockTransport = nil
        networkClient = nil
        super.tearDown()
    }

    // MARK: - 1. HomeViewModel Initial State (NAV-02)

    @MainActor
    func testHomeViewModelInitialState() {
        let viewModel = HomeViewModel(networkClient: networkClient)

        XCTAssertTrue(viewModel.recentAnalyses.isEmpty)
        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.errorMessage)
        XCTAssertFalse(viewModel.isPopulated)
        XCTAssertTrue(viewModel.isEmpty)
    }

    // MARK: - 2. Load Recent Activity Success (NAV-04)

    @MainActor
    func testLoadRecentActivitySuccessWith3Items() async throws {
        let isoFormatter = ISO8601DateFormatter()
        let nowString = isoFormatter.string(from: Date())

        let json = """
        {
            "items": [
                {
                    "id": 101,
                    "modality": "IMAGE",
                    "status": "completed",
                    "verdict": "Suitable",
                    "processing_duration_ms": 450,
                    "created_at": "\(nowString)"
                },
                {
                    "id": 102,
                    "modality": "TEXT",
                    "status": "completed",
                    "verdict": "Not Suitable",
                    "processing_duration_ms": 320,
                    "created_at": "\(nowString)"
                },
                {
                    "id": 103,
                    "modality": "AUDIO",
                    "status": "completed",
                    "verdict": "Caution",
                    "processing_duration_ms": 890,
                    "created_at": "\(nowString)"
                }
            ],
            "total": 3,
            "limit": 3,
            "offset": 0
        }
        """

        mockTransport.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/analyses")
            XCTAssertTrue(request.url?.query?.contains("limit=3") ?? false)
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (Data(json.utf8), response)
        }

        let viewModel = HomeViewModel(networkClient: networkClient)
        await viewModel.loadRecentActivity()

        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.errorMessage)
        XCTAssertTrue(viewModel.isPopulated)
        XCTAssertFalse(viewModel.isEmpty)
        XCTAssertEqual(viewModel.recentAnalyses.count, 3)
        XCTAssertEqual(viewModel.recentAnalyses[0].id, 101)
        XCTAssertEqual(viewModel.recentAnalyses[0].modality, "IMAGE")
        XCTAssertEqual(viewModel.recentAnalyses[1].id, 102)
        XCTAssertEqual(viewModel.recentAnalyses[2].id, 103)
    }

    // MARK: - 3. Load Recent Activity Caps At 3 Items (NAV-04)

    @MainActor
    func testLoadRecentActivityCapsAtMax3() async throws {
        let isoFormatter = ISO8601DateFormatter()
        let nowString = isoFormatter.string(from: Date())

        let json = """
        {
            "items": [
                {"id": 1, "modality": "IMAGE", "status": "completed", "verdict": "Safe", "created_at": "\(nowString)"},
                {"id": 2, "modality": "IMAGE", "status": "completed", "verdict": "Safe", "created_at": "\(nowString)"},
                {"id": 3, "modality": "TEXT", "status": "completed", "verdict": "Safe", "created_at": "\(nowString)"},
                {"id": 4, "modality": "AUDIO", "status": "completed", "verdict": "Safe", "created_at": "\(nowString)"},
                {"id": 5, "modality": "IMAGE", "status": "completed", "verdict": "Safe", "created_at": "\(nowString)"}
            ],
            "total": 5,
            "limit": 5,
            "offset": 0
        }
        """

        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (Data(json.utf8), response)
        }

        let viewModel = HomeViewModel(networkClient: networkClient)
        await viewModel.loadRecentActivity()

        XCTAssertEqual(viewModel.recentAnalyses.count, 3, "Recent activity must strictly cap at 3 items.")
        XCTAssertEqual(viewModel.recentAnalyses.map(\.id), [1, 2, 3])
    }

    // MARK: - 4. Empty State Verification (NAV-04)

    @MainActor
    func testLoadRecentActivityEmptyState() async throws {
        let json = """
        {
            "items": [],
            "total": 0,
            "limit": 3,
            "offset": 0
        }
        """

        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            return (Data(json.utf8), response)
        }

        let viewModel = HomeViewModel(networkClient: networkClient)
        await viewModel.loadRecentActivity()

        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNil(viewModel.errorMessage)
        XCTAssertTrue(viewModel.recentAnalyses.isEmpty)
        XCTAssertTrue(viewModel.isEmpty)
        XCTAssertFalse(viewModel.isPopulated)
    }

    // MARK: - 5. Error Handling & Session Expiry (NAV-04)

    @MainActor
    func testLoadRecentActivityServerError() async {
        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 500,
                httpVersion: nil,
                headerFields: nil
            )!
            return (Data(), response)
        }

        let viewModel = HomeViewModel(networkClient: networkClient)
        await viewModel.loadRecentActivity()

        XCTAssertFalse(viewModel.isLoading)
        XCTAssertNotNil(viewModel.errorMessage)
        XCTAssertTrue(viewModel.recentAnalyses.isEmpty)
        XCTAssertFalse(viewModel.isEmpty)
    }

    @MainActor
    func testLoadRecentActivityUnauthorized() async {
        mockTransport.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 401,
                httpVersion: nil,
                headerFields: nil
            )!
            return (Data(), response)
        }

        let viewModel = HomeViewModel(networkClient: networkClient)
        await viewModel.loadRecentActivity()

        XCTAssertFalse(viewModel.isLoading)
        XCTAssertEqual(viewModel.errorMessage, "Session expired. Please sign in again.")
    }

    // MARK: - 6. Relative Timestamp Formatting (NAV-04)

    func testRelativeTimestampFormatting() {
        let now = Date()

        // Less than 60 seconds ago -> "Just now"
        let recent = now.addingTimeInterval(-25)
        XCTAssertEqual(HomeViewModel.relativeTimestamp(for: recent, relativeTo: now), "Just now")

        // 10 minutes ago
        let tenMinsAgo = now.addingTimeInterval(-600)
        let tenMinsText = HomeViewModel.relativeTimestamp(for: tenMinsAgo, relativeTo: now)
        XCTAssertTrue(tenMinsText.contains("10") || tenMinsText.contains("minute"))

        // 2 hours ago
        let twoHoursAgo = now.addingTimeInterval(-7200)
        let twoHoursText = HomeViewModel.relativeTimestamp(for: twoHoursAgo, relativeTo: now)
        XCTAssertTrue(twoHoursText.contains("2") || twoHoursText.contains("hour"))
    }

    // MARK: - 7. AppCoordinator Programmatic Tab Switching (NAV-01)

    @MainActor
    func testAppCoordinatorTabSelection() {
        let coordinator = AppCoordinator()

        XCTAssertEqual(coordinator.selectedTab, .home)

        coordinator.selectTab(.scan)
        XCTAssertEqual(coordinator.selectedTab, .scan)

        coordinator.selectTab(.history)
        XCTAssertEqual(coordinator.selectedTab, .history)

        coordinator.selectTab(.profile)
        XCTAssertEqual(coordinator.selectedTab, .profile)

        coordinator.selectTab(.home)
        XCTAssertEqual(coordinator.selectedTab, .home)
    }

    // MARK: - 8. Clinical Verdict Status Mapping (NAV-04)

    func testClinicalVerdictStatusMapping() {
        let itemDanger = AnalysisListItem(id: 1, modality: "IMAGE", status: "completed", verdict: "Not Suitable for patient")
        XCTAssertEqual(itemDanger.verdictStatus, .danger)

        let itemSuccess = AnalysisListItem(id: 2, modality: "IMAGE", status: "completed", verdict: "Suitable and verified")
        XCTAssertEqual(itemSuccess.verdictStatus, .success)

        let itemWarning = AnalysisListItem(id: 3, modality: "TEXT", status: "completed", verdict: "Caution: Moderate interaction")
        XCTAssertEqual(itemWarning.verdictStatus, .warning)

        let itemNeutral = AnalysisListItem(id: 4, modality: "AUDIO", status: "completed", verdict: "Consult clinician")
        XCTAssertEqual(itemNeutral.verdictStatus, .neutral)

        let itemFailed = AnalysisListItem(id: 5, modality: "IMAGE", status: "failed", verdict: nil)
        XCTAssertEqual(itemFailed.verdictStatus, .danger)
    }

    // MARK: - 9. Modality Icon Mapping (NAV-04)

    func testModalityIconMapping() {
        let imageItem = AnalysisListItem(id: 1, modality: "IMAGE", status: "completed")
        XCTAssertEqual(imageItem.modalityIcon, "camera.fill")

        let textItem = AnalysisListItem(id: 2, modality: "TEXT", status: "completed")
        XCTAssertEqual(textItem.modalityIcon, "text.bubble.fill")

        let audioItem = AnalysisListItem(id: 3, modality: "AUDIO", status: "completed")
        XCTAssertEqual(audioItem.modalityIcon, "waveform")

        let multimodalItem = AnalysisListItem(id: 4, modality: "MULTIMODAL", status: "completed")
        XCTAssertEqual(multimodalItem.modalityIcon, "sparkles")

        let unknownItem = AnalysisListItem(id: 5, modality: "DOC", status: "completed")
        XCTAssertEqual(unknownItem.modalityIcon, "doc.text.fill")
    }
}
