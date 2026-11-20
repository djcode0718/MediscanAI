import XCTest

final class DesignSystemUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testDesignSystemPreviewRendersDirectly() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-UITest_DesignSystemPreview"]
        app.launch()

        // 1. Verify preview container is visible
        let previewContainer = app.otherElements["DesignSystemPreviewView"]
        XCTAssertTrue(previewContainer.waitForExistence(timeout: 5.0), "DesignSystemPreviewView should be visible when launched with argument.")

        // 2. Verify Key Headers
        XCTAssertTrue(app.staticTexts["Design System"].exists, "Main title should exist.")
        XCTAssertTrue(app.staticTexts["Color Tokens"].exists, "Color Tokens section header should exist.")
        XCTAssertTrue(app.staticTexts["Typography Scale"].exists, "Typography Scale section header should exist.")
        XCTAssertTrue(app.staticTexts["Spacing & Radii"].exists, "Spacing & Radii section header should exist.")
        XCTAssertTrue(app.staticTexts["Buttons"].exists, "Buttons section header should exist.")
        XCTAssertTrue(app.staticTexts["Surface Cards"].exists, "Cards section header should exist.")
        XCTAssertTrue(app.staticTexts["Form Controls"].exists, "Form Controls section header should exist.")
        XCTAssertTrue(app.staticTexts["Verdict Badges"].exists, "Verdict Badges section header should exist.")

        // 3. Verify Buttons are interactable
        let primaryBtn = app.buttons["Preview_PrimaryButton"]
        XCTAssertTrue(primaryBtn.exists, "Primary button should be visible.")
        primaryBtn.tap()

        let tapCounter = app.staticTexts["Preview_TapCounter"]
        XCTAssertTrue(tapCounter.exists, "Tap counter should exist.")
        XCTAssertEqual(tapCounter.label, "Taps: 1")

        // 4. Verify Verdict Badges
        let dangerBadge = app.otherElements["Preview_VerdictDanger"]
        let successBadge = app.otherElements["Preview_VerdictSuccess"]
        XCTAssertTrue(dangerBadge.exists || app.staticTexts["Not Suitable"].exists, "Danger verdict pill should exist.")
        XCTAssertTrue(successBadge.exists || app.staticTexts["Suitable"].exists, "Success verdict pill should exist.")
    }

    func testLaunchScreenCanOpenDesignSystemSheet() throws {
        let app = XCUIApplication()
        app.launch() // Launch without argument -> opens FoundationLaunchView

        // Verify foundation launch screen
        let exploreButton = app.buttons["ExploreDesignSystemButton"]
        XCTAssertTrue(exploreButton.waitForExistence(timeout: 5.0), "Explore Design System button should be visible on foundation screen.")

        // Tap to open sheet
        exploreButton.tap()

        // Verify design system preview sheet opens
        let previewContainer = app.otherElements["DesignSystemPreviewView"]
        XCTAssertTrue(previewContainer.waitForExistence(timeout: 5.0), "DesignSystemPreviewView should open via sheet.")
    }
}
