import XCTest
@testable import MediScanAI

final class MediScanAITests: XCTestCase {

    func testAppEnvironmentMetadata() {
        let env = AppEnvironment()
        XCTAssertEqual(env.appName, "MediScanAI")
        XCTAssertEqual(env.appVersion, "1.0.0")
        XCTAssertEqual(env.buildNumber, "1")
    }
    
    func testAppEnvironmentDefaultBaseURL() {
        let env = AppEnvironment()
        XCTAssertEqual(env.defaultBaseURL.scheme, "http")
        XCTAssertEqual(env.defaultBaseURL.port, 8000)
        XCTAssertFalse(env.defaultBaseURL.absoluteString.isEmpty)
    }
    
    func testAppCoordinatorInitialState() {
        let coordinator = AppCoordinator()
        XCTAssertEqual(coordinator.currentDestination, .foundation)
        
        coordinator.resetToFoundation()
        XCTAssertEqual(coordinator.currentDestination, .foundation)
    }
}

