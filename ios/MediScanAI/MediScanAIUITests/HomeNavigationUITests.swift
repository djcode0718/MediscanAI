import XCTest

// MARK: - Home Navigation UI Tests (NAV-01 through NAV-04)

final class HomeNavigationUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    private func launchAuthenticatedApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments.append("-UITest_AuthenticatedUser")
        app.launch()
        return app
    }

    // MARK: - 1. Four-Tab Shell & Home Elements Rendered (NAV-01, NAV-02)

    func testAuthenticatedHomeRendersFourTabsAndDashboard() throws {
        let app = launchAuthenticatedApp()

        // Verify Tab bar elements exist
        let mainTabView = app.otherElements["MainTabView"]
        XCTAssertTrue(mainTabView.waitForExistence(timeout: 5.0), "MainTabView should appear when authenticated.")

        let homeTab = app.tabBars.buttons["Home"]
        XCTAssertTrue(homeTab.exists, "Home tab bar button should exist.")

        let scanTab = app.tabBars.buttons["Scan"]
        XCTAssertTrue(scanTab.exists, "Scan tab bar button should exist.")

        let historyTab = app.tabBars.buttons["History"]
        XCTAssertTrue(historyTab.exists, "History tab bar button should exist.")

        let profileTab = app.tabBars.buttons["Profile"]
        XCTAssertTrue(profileTab.exists, "Profile tab bar button should exist.")

        // Verify Brand Header & Connection Badge
        let brandHeader = app.staticTexts["MEDISCAN"]
        XCTAssertTrue(brandHeader.exists, "Brand header should exist.")

        let connectionBadge = app.buttons["Home_ServerConnectionBadge"]
        XCTAssertTrue(connectionBadge.exists, "Server connection badge should exist on Home screen.")

        // Verify Greeting
        let greetingTitle = app.staticTexts["Home_GreetingTitle"]
        XCTAssertTrue(greetingTitle.exists, "Greeting title should exist.")
        XCTAssertTrue(greetingTitle.label.contains("Dr. Jane Foster"), "Greeting should display user's full name.")

        // Verify Quick Action Cards (NAV-03)
        let scanHero = app.buttons["Home_ScanMedicineCard"]
        XCTAssertTrue(scanHero.exists, "Scan Medicine hero card should exist.")

        let enterSymptoms = app.buttons["Home_EnterSymptomsCard"]
        XCTAssertTrue(enterSymptoms.exists, "Enter Symptoms card should exist.")

        let voiceRecording = app.buttons["Home_VoiceRecordingCard"]
        XCTAssertTrue(voiceRecording.exists, "Voice Recording card should exist.")

        // Verify Recent Activity Section Header
        let viewAllButton = app.buttons["Home_ViewAllHistoryButton"]
        XCTAssertTrue(viewAllButton.exists, "View All button should exist in Recent Activity header.")
    }

    // MARK: - 2. Hero Scan Medicine Navigates to Scan Tab (NAV-03)

    func testHeroScanMedicineNavigatesToScanTab() throws {
        let app = launchAuthenticatedApp()

        let scanHero = app.buttons["Home_ScanMedicineCard"]
        XCTAssertTrue(scanHero.waitForExistence(timeout: 5.0))
        scanHero.tap()

        // Scan tab destination placeholder should be displayed
        let scanHeader = app.staticTexts["Medicine Scan"]
        XCTAssertTrue(scanHeader.waitForExistence(timeout: 3.0), "Tapping hero card should switch to Scan tab.")
    }

    // MARK: - 3. Secondary Quick Actions Open Sheets (NAV-03)

    func testSecondaryQuickActionEnterSymptomsOpensSheet() throws {
        let app = launchAuthenticatedApp()

        let enterSymptoms = app.buttons["Home_EnterSymptomsCard"]
        XCTAssertTrue(enterSymptoms.waitForExistence(timeout: 5.0))
        enterSymptoms.tap()

        let symptomSheet = app.otherElements["SymptomComposerPlaceholderSheet"]
        XCTAssertTrue(symptomSheet.waitForExistence(timeout: 3.0), "Enter symptoms sheet should open.")

        let doneButton = app.buttons["SymptomComposer_DoneButton"]
        XCTAssertTrue(doneButton.exists)
        doneButton.tap()

        XCTAssertFalse(symptomSheet.waitForExistence(timeout: 2.0), "Sheet should dismiss.")
    }

    func testSecondaryQuickActionVoiceRecordingOpensSheet() throws {
        let app = launchAuthenticatedApp()

        let voiceRecording = app.buttons["Home_VoiceRecordingCard"]
        XCTAssertTrue(voiceRecording.waitForExistence(timeout: 5.0))
        voiceRecording.tap()

        let voiceSheet = app.otherElements["VoiceRecordingPlaceholderSheet"]
        XCTAssertTrue(voiceSheet.waitForExistence(timeout: 3.0), "Voice recording sheet should open.")

        let doneButton = app.buttons["VoiceRecording_DoneButton"]
        XCTAssertTrue(doneButton.exists)
        doneButton.tap()

        XCTAssertFalse(voiceSheet.waitForExistence(timeout: 2.0), "Sheet should dismiss.")
    }

    // MARK: - 4. View All Switches to History Tab (NAV-04)

    func testViewAllHistorySwitchesToHistoryTab() throws {
        let app = launchAuthenticatedApp()

        let viewAllButton = app.buttons["Home_ViewAllHistoryButton"]
        XCTAssertTrue(viewAllButton.waitForExistence(timeout: 5.0))
        viewAllButton.tap()

        let historyHeader = app.staticTexts["Analysis History"]
        XCTAssertTrue(historyHeader.waitForExistence(timeout: 3.0), "Tapping View All should switch to History tab.")
    }

    // MARK: - 5. Tab Bar Direct Switching Across All Tabs (NAV-01)

    func testTabBarSwitchingAcrossAllTabs() throws {
        let app = launchAuthenticatedApp()

        // 1. Switch to Scan Tab
        let scanTab = app.tabBars.buttons["Scan"]
        XCTAssertTrue(scanTab.waitForExistence(timeout: 5.0))
        scanTab.tap()
        XCTAssertTrue(app.staticTexts["Medicine Scan"].waitForExistence(timeout: 3.0))

        // 2. Switch to History Tab
        let historyTab = app.tabBars.buttons["History"]
        historyTab.tap()
        XCTAssertTrue(app.staticTexts["Analysis History"].waitForExistence(timeout: 3.0))

        // 3. Switch to Profile Tab
        let profileTab = app.tabBars.buttons["Profile"]
        profileTab.tap()
        XCTAssertTrue(app.staticTexts["Clinician Profile"].waitForExistence(timeout: 3.0))

        // 4. Switch back to Home Tab
        let homeTab = app.tabBars.buttons["Home"]
        homeTab.tap()
        XCTAssertTrue(app.staticTexts["Home_GreetingTitle"].waitForExistence(timeout: 3.0))
    }
}
