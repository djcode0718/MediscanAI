import XCTest

final class MediScanAIUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLaunchAndFoundationScreenVisible() throws {
        let app = XCUIApplication()
        app.launch()

        // Verify MediScanAI branding label is present
        let brandingText = app.staticTexts["MediScanAI"]
        XCTAssertTrue(brandingText.waitForExistence(timeout: 5.0), "MediScanAI branding should be visible on initial launch.")

        // Verify placeholder subtitle is present
        let subtitleText = app.staticTexts["Your AI-powered health companion."]
        XCTAssertTrue(subtitleText.exists, "Subtitle should be present on the foundation screen.")
        
        // Verify foundation phase status label
        let phaseLabel = app.staticTexts["Phase 1 · Core Foundation"]
        XCTAssertTrue(phaseLabel.exists, "Phase 1 status indicator should be present.")
    }
}

