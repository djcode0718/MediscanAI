import SwiftUI

/// Main entry point for the native MediScanAI iOS application.
@main
struct MediScanAIApp: App {
    @State private var environment = AppEnvironment()
    @State private var coordinator = AppCoordinator()

    var body: some Scene {
        WindowGroup {
            RootContentView()
                .environment(environment)
                .environment(coordinator)
                .preferredColorScheme(.dark)
                .task {
                    await environment.authManager.restoreSession()
                }
        }
    }
}

/// Root view switching between session restoration splash, authenticated placeholder,
/// unauthenticated login, or development-only design system preview.
struct RootContentView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator

    var body: some View {
        Group {
            #if DEBUG
            if ProcessInfo.processInfo.arguments.contains("-UITest_DesignSystemPreview") || coordinator.currentDestination == .designSystemPreview {
                DesignSystemPreviewView()
            } else if environment.authManager.isRestoringSession {
                SessionRestoringSplashView()
            } else if environment.authManager.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
            #else
            if environment.authManager.isRestoringSession {
                SessionRestoringSplashView()
            } else if environment.authManager.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
            #endif
        }
    }
}

/// Monochromatic OLED splash view displayed while inspecting Keychain and validating token.
struct SessionRestoringSplashView: View {
    var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            VStack(spacing: AppSpacing.large) {
                ZStack {
                    RoundedRectangle(cornerRadius: AppRadius.modal, style: .continuous)
                        .fill(AppColors.surfaceSecondary)
                        .frame(width: 88, height: 88)
                        .overlay(
                            RoundedRectangle(cornerRadius: AppRadius.modal, style: .continuous)
                                .stroke(AppColors.borderSubtle, lineWidth: 1)
                        )

                    Image(systemName: "cross.case.fill")
                        .font(.system(size: 38, weight: .semibold))
                        .foregroundColor(AppColors.textPrimary)
                }

                StatusIndicator(size: 44)

                Text("Restoring session...")
                    .font(.appSubheadline)
                    .foregroundColor(AppColors.textSecondary)
            }
        }
    }
}
