import XCTest

final class ServerConnectionUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testServerConnectionBadgeIsPresentOnLogin() throws {
        let app = XCUIApplication()
        app.launch()

        // Verify ServerConnectionBadge is present
        let badge = app.buttons["ServerConnectionBadge_Button"]
        XCTAssertTrue(badge.waitForExistence(timeout: 5.0), "Server connection badge should be visible on login screen.")
    }

    func testTappingBadgeOpensServerConfigSheetAndDismisses() throws {
        let app = XCUIApplication()
        app.launch()

        // Tap Connection Badge
        let badge = app.buttons["ServerConnectionBadge_Button"]
        XCTAssertTrue(badge.waitForExistence(timeout: 5.0))
        badge.tap()

        // Verify Server Config Sheet Elements
        let urlField = app.textFields["ServerConfig_URLTextField"]
        XCTAssertTrue(urlField.waitForExistence(timeout: 3.0), "URL text field should be visible in ServerConfigSheet.")

        let saveButton = app.buttons["ServerConfig_SaveButton"]
        XCTAssertTrue(saveButton.exists, "Save & Apply button should exist.")

        let resetButton = app.buttons["ServerConfig_ResetButton"]
        XCTAssertTrue(resetButton.exists, "Reset button should exist.")

        let testButton = app.buttons["ServerConfig_TestButton"]
        XCTAssertTrue(testButton.exists, "Test Connection button should exist.")

        // Tap Done to Dismiss
        let doneButton = app.buttons["ServerConfig_DoneButton"]
        XCTAssertTrue(doneButton.exists, "Done button should exist in toolbar.")
        doneButton.tap()

        // Verify we are back on Login Screen
        XCTAssertTrue(badge.waitForExistence(timeout: 3.0), "Badge should be visible after dismissing sheet.")
    }

    func testServerConfigValidationFeedback() throws {
        let app = XCUIApplication()
        app.launch()

        let badge = app.buttons["ServerConnectionBadge_Button"]
        XCTAssertTrue(badge.waitForExistence(timeout: 5.0))
        badge.tap()

        let urlField = app.textFields["ServerConfig_URLTextField"]
        XCTAssertTrue(urlField.waitForExistence(timeout: 3.0))

        // Clear text field and type invalid URL
        urlField.tap()
        let existingText = urlField.value as? String ?? ""
        let deleteString = String(repeating: XCUIKeyboardKey.delete.rawValue, count: max(existingText.count, 35))
        urlField.typeText(deleteString)
        urlField.typeText("ftp://invalid:8000")

        // Save button must be disabled for unsupported scheme
        let saveButton = app.buttons["ServerConfig_SaveButton"]
        XCTAssertFalse(saveButton.isEnabled, "Save button should be disabled for unsupported scheme.")

        // Dismiss sheet
        app.buttons["ServerConfig_DoneButton"].tap()
    }
}
