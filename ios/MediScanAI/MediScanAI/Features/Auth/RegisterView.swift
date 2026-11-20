import SwiftUI

// MARK: - Register View (AUTH-03, AUTH-06)

public struct RegisterView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(AppEnvironment.self) private var environment
    @State private var viewModel = AuthenticationViewModel(isRegisterMode: true)

    public init() {}

    public var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: AppSpacing.large) {
                    // Header
                    VStack(spacing: AppSpacing.compact) {
                        Text("Create Account")
                            .font(.appTitle1)
                            .foregroundColor(AppColors.textPrimary)

                        Text("Join MediScanAI to securely analyze medical reports and monitor symptoms.")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textSecondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding(.top, AppSpacing.large)

                    // Error Banner
                    if let error = viewModel.errorMessage {
                        NoticeBanner(
                            variant: .warning,
                            title: "Registration Error",
                            message: error
                        )
                        .accessibilityIdentifier("Register_ErrorBanner")
                        .transition(.opacity.combined(with: .scale(scale: 0.98)))
                    }

                    // Form Fields Card
                    AppCard {
                        VStack(spacing: AppSpacing.standard) {
                            AppTextField(
                                title: "Full Name (Optional)",
                                placeholder: "Dr. Sarah Connor",
                                text: $viewModel.fullName,
                                leadingIcon: "person.fill"
                            )
                            .accessibilityIdentifier("Register_FullNameTextField")

                            AppTextField(
                                title: "Email Address",
                                placeholder: "doctor@hospital.org",
                                text: $viewModel.email,
                                leadingIcon: "envelope.fill"
                            )
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled(true)
                            .keyboardType(.emailAddress)
                            .accessibilityIdentifier("Register_EmailTextField")

                            AppTextField(
                                title: "Password (Min 6 characters)",
                                placeholder: "••••••••",
                                text: $viewModel.password,
                                leadingIcon: "lock.fill",
                                isSecure: true
                            )
                            .accessibilityIdentifier("Register_PasswordTextField")

                            AppTextField(
                                title: "Confirm Password",
                                placeholder: "••••••••",
                                text: $viewModel.confirmPassword,
                                leadingIcon: "lock.shield.fill",
                                isSecure: true
                            )
                            .accessibilityIdentifier("Register_ConfirmPasswordTextField")

                            PrimaryButton(
                                "Create Account",
                                icon: "checkmark",
                                isLoading: viewModel.isLoading,
                                isEnabled: viewModel.isRegisterFormValid
                            ) {
                                Task {
                                    let success = await viewModel.register(authManager: environment.authManager)
                                    if success {
                                        dismiss()
                                    }
                                }
                            }
                            .accessibilityIdentifier("Register_SubmitButton")
                            .padding(.top, AppSpacing.compact)
                        }
                    }

                    // Back to Login Link
                    Button(action: {
                        dismiss()
                    }) {
                        HStack(spacing: AppSpacing.micro) {
                            Text("Already have an account?")
                                .foregroundColor(AppColors.textSecondary)
                            Text("Sign In")
                                .foregroundColor(AppColors.textPrimary)
                                .fontWeight(.semibold)
                        }
                        .font(.appSubheadline)
                        .padding(.vertical, AppSpacing.compact)
                    }
                    .accessibilityIdentifier("Register_BackToLoginButton")
                }
                .padding(.horizontal, AppSpacing.extraLarge)
                .padding(.bottom, AppSpacing.extraLarge)
            }
        }
        .navigationBarBackButtonHidden(false)
        .toolbarBackground(AppColors.background, for: .navigationBar)
        .toolbarColorScheme(.dark, for: .navigationBar)
    }
}
