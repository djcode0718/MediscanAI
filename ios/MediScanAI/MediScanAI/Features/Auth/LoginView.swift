import SwiftUI

// MARK: - Login View (AUTH-06)

public struct LoginView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var viewModel = AuthenticationViewModel()
    @State private var isShowingRegister: Bool = false
    #if DEBUG
    @State private var showDesignSystemSheet: Bool = false
    #endif

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: AppSpacing.large) {
                        // Brand Header
                        VStack(spacing: AppSpacing.standard) {
                            ZStack {
                                RoundedRectangle(cornerRadius: AppRadius.modal, style: .continuous)
                                    .fill(AppColors.surfaceSecondary)
                                    .frame(width: 80, height: 80)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: AppRadius.modal, style: .continuous)
                                            .stroke(AppColors.borderSubtle, lineWidth: 1)
                                    )

                                Image(systemName: "cross.case.fill")
                                    .font(.system(size: 34, weight: .semibold))
                                    .foregroundColor(AppColors.textPrimary)
                            }
                            .accessibilityHidden(true)

                            VStack(spacing: AppSpacing.micro) {
                                Text("MediScanAI")
                                    .font(.appLargeTitle)
                                    .foregroundColor(AppColors.textPrimary)
                                    .accessibilityLabel("MediScanAI")

                                Text("Your AI-powered health companion.")
                                    .font(.appBody)
                                    .foregroundColor(AppColors.textSecondary)
                                    .multilineTextAlignment(.center)
                                    .accessibilityLabel("Your AI-powered health companion.")
                            }
                        }
                        .padding(.top, AppSpacing.large)

                        // Subtitle & Guidance
                        Text("Sign in to access clinical records and AI insights.")
                            .font(.appSubheadline)
                            .foregroundColor(AppColors.textTertiary)
                            .multilineTextAlignment(.center)

                        // Server Connection Status Badge (WIFI-03)
                        ServerConnectionBadge()

                        // Error Banner
                        if let error = viewModel.errorMessage {
                            NoticeBanner(
                                variant: .warning,
                                title: "Authentication Failed",
                                message: error
                            )
                            .accessibilityIdentifier("Login_ErrorBanner")
                            .transition(.opacity.combined(with: .scale(scale: 0.98)))
                        }

                        // Input Card
                        AppCard {
                            VStack(spacing: AppSpacing.standard) {
                                AppTextField(
                                    title: "Email Address",
                                    placeholder: "doctor@hospital.org",
                                    text: $viewModel.email,
                                    leadingIcon: "envelope.fill"
                                )
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled(true)
                                .keyboardType(.emailAddress)
                                .accessibilityIdentifier("Login_EmailTextField")

                                AppTextField(
                                    title: "Password",
                                    placeholder: "••••••••",
                                    text: $viewModel.password,
                                    leadingIcon: "lock.fill",
                                    isSecure: true
                                )
                                .accessibilityIdentifier("Login_PasswordTextField")

                                PrimaryButton(
                                    "Sign In",
                                    icon: "arrow.right",
                                    isLoading: viewModel.isLoading,
                                    isEnabled: viewModel.isLoginFormValid
                                ) {
                                    Task {
                                        _ = await viewModel.signIn(authManager: environment.authManager)
                                    }
                                }
                                .accessibilityIdentifier("Login_SubmitButton")
                                .padding(.top, AppSpacing.compact)
                            }
                        }

                        // Switch to Register
                        Button(action: {
                            isShowingRegister = true
                        }) {
                            HStack(spacing: AppSpacing.micro) {
                                Text("Don't have an account?")
                                    .foregroundColor(AppColors.textSecondary)
                                Text("Create Account")
                                    .foregroundColor(AppColors.textPrimary)
                                    .fontWeight(.semibold)
                            }
                            .font(.appSubheadline)
                            .padding(.vertical, AppSpacing.compact)
                        }
                        .accessibilityIdentifier("Login_GoToRegisterButton")

                        #if DEBUG
                        // Development-only Design System Preview access
                        SecondaryButton("Explore Design System", icon: "square.grid.2x2") {
                            showDesignSystemSheet = true
                        }
                        .frame(maxWidth: 260)
                        .accessibilityIdentifier("ExploreDesignSystemButton")
                        #endif

                        // Foundation Status Capsule
                        HStack(spacing: AppSpacing.compact) {
                            Circle()
                                .fill(AppColors.statusSuccess)
                                .frame(width: 6, height: 6)

                            Text("Phase 1 · Core Foundation")
                                .font(.appCaption1)
                                .monospacedDigit()
                                .foregroundColor(AppColors.textTertiary)
                        }
                        .padding(.horizontal, AppSpacing.standard)
                        .padding(.vertical, AppSpacing.compact)
                        .background(
                            Capsule()
                                .fill(AppColors.surfacePrimary)
                                .overlay(
                                    Capsule()
                                        .stroke(AppColors.borderSubtle, lineWidth: 1)
                                )
                        )
                        .padding(.bottom, AppSpacing.extraLarge)
                    }
                    .padding(.horizontal, AppSpacing.extraLarge)
                }
            }
            .navigationDestination(isPresented: $isShowingRegister) {
                RegisterView()
            }
            #if DEBUG
            .sheet(isPresented: $showDesignSystemSheet) {
                DesignSystemPreviewView()
            }
            #endif
        }
    }
}
