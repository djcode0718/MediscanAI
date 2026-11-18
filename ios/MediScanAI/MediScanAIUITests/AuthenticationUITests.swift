import XCTest

final class AuthenticationUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLoginViewElementsPresent() throws {
        let app = XCUIApplication()
        app.launch()

        // Verify MediScanAI Branding
        let branding = app.staticTexts["MediScanAI"]
        XCTAssertTrue(branding.waitForExistence(timeout: 5.0), "MediScanAI branding should be visible on login screen.")

        // Verify Email & Password input fields exist
        let emailField = app.textFields["Login_EmailTextField"]
        XCTAssertTrue(emailField.exists, "Login email text field should exist.")

        let passwordField = app.secureTextFields["Login_PasswordTextField"]
        XCTAssertTrue(passwordField.exists, "Login password secure text field should exist.")

        // Verify Submit Button exists
        let submitBtn = app.buttons["Login_SubmitButton"]
        XCTAssertTrue(submitBtn.exists, "Login submit button should exist.")

        // Verify Switch to Register link exists
        let goToRegisterBtn = app.buttons["Login_GoToRegisterButton"]
        XCTAssertTrue(goToRegisterBtn.exists, "Link to register view should exist.")
    }

    func testNavigateToRegistrationAndBack() throws {
        let app = XCUIApplication()
        app.launch()

        // Tap Go to Register
        let goToRegisterBtn = app.buttons["Login_GoToRegisterButton"]
        XCTAssertTrue(goToRegisterBtn.waitForExistence(timeout: 5.0))
        goToRegisterBtn.tap()

        // Verify Register View Elements
        let registerHeader = app.staticTexts["Create Account"]
        XCTAssertTrue(registerHeader.waitForExistence(timeout: 3.0), "Register view title should appear.")

        let fullNameField = app.textFields["Register_FullNameTextField"]
        XCTAssertTrue(fullNameField.exists, "Full name input should exist in registration view.")

        let confirmPasswordField = app.secureTextFields["Register_ConfirmPasswordTextField"]
        XCTAssertTrue(confirmPasswordField.exists, "Confirm password field should exist in registration view.")

        // Tap Back to Login
        let backToLoginBtn = app.buttons["Register_BackToLoginButton"]
        XCTAssertTrue(backToLoginBtn.exists, "Back to Login button should exist.")
        backToLoginBtn.tap()

        // Verify we are back on Login Screen
        let loginSubmitBtn = app.buttons["Login_SubmitButton"]
        XCTAssertTrue(loginSubmitBtn.waitForExistence(timeout: 3.0), "Should return to login screen.")
    }
}
