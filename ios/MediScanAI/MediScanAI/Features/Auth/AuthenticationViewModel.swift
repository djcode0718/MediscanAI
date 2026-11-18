import Foundation
import SwiftUI

// MARK: - Authentication View Model (AUTH-03, AUTH-04, AUTH-06)

@Observable
@MainActor
public final class AuthenticationViewModel {
    public var email: String = ""
    public var password: String = ""
    public var fullName: String = ""
    public var confirmPassword: String = ""

    public var isRegisterMode: Bool = false
    public var isLoading: Bool = false
    public var errorMessage: String? = nil

    public init(
        initialEmail: String = "",
        isRegisterMode: Bool = false
    ) {
        self.email = initialEmail
        self.isRegisterMode = isRegisterMode
    }

    // MARK: - Form Validation

    public var isEmailValid: Bool {
        let trimmed = email.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return false }
        let emailRegex = #"^[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,64}$"#
        return NSPredicate(format: "SELF MATCHES %@", emailRegex).evaluate(with: trimmed)
    }

    public var isPasswordValid: Bool {
        password.count >= 6
    }

    public var doPasswordsMatch: Bool {
        !password.isEmpty && password == confirmPassword
    }

    public var isLoginFormValid: Bool {
        isEmailValid && !password.isEmpty
    }

    public var isRegisterFormValid: Bool {
        isEmailValid && isPasswordValid && doPasswordsMatch
    }

    // MARK: - Actions

    public func signIn(authManager: AuthManager) async -> Bool {
        guard isLoginFormValid else {
            errorMessage = "Please enter a valid email address and password."
            return false
        }

        clearError()
        isLoading = true
        defer { isLoading = false }

        do {
            _ = try await authManager.login(email: email, password: password)
            return true
        } catch let apiError as APIError {
            switch apiError {
            case .unauthorized(let detail):
                errorMessage = detail ?? "Invalid email or password."
            case .badRequest(let detail):
                errorMessage = detail ?? "Invalid login request."
            case .serverError(let code, let detail):
                errorMessage = detail ?? "Server error (\(code)). Please try again later."
            case .noConnection:
                errorMessage = "No network connection. Please check your Wi-Fi or cellular network."
            case .timeout:
                errorMessage = "Connection timed out. Please check network."
            default:
                errorMessage = apiError.localizedDescription
            }
            return false
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    public func register(authManager: AuthManager) async -> Bool {
        guard isRegisterFormValid else {
            if !isEmailValid {
                errorMessage = "Please enter a valid email address."
            } else if !isPasswordValid {
                errorMessage = "Password must be at least 6 characters."
            } else if !doPasswordsMatch {
                errorMessage = "Passwords do not match."
            }
            return false
        }

        clearError()
        isLoading = true
        defer { isLoading = false }

        do {
            _ = try await authManager.register(
                email: email,
                password: password,
                fullName: fullName.isEmpty ? nil : fullName
            )
            return true
        } catch let apiError as APIError {
            switch apiError {
            case .badRequest(let detail):
                errorMessage = detail ?? "Registration failed. An account with this email may already exist."
            case .serverError(let code, let detail):
                errorMessage = detail ?? "Server error (\(code)). Please try again later."
            case .noConnection:
                errorMessage = "No network connection. Please check your Wi-Fi or cellular network."
            case .timeout:
                errorMessage = "Connection timed out. Please check network."
            default:
                errorMessage = apiError.localizedDescription
            }
            return false
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    public func clearError() {
        errorMessage = nil
    }

    public func toggleMode() {
        clearError()
        isRegisterMode.toggle()
    }
}
