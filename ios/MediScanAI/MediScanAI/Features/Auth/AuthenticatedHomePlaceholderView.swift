import SwiftUI

// MARK: - Authenticated Home Placeholder (Phase 4 Minimal Screen)

public struct AuthenticatedHomePlaceholderView: View {
    @Environment(AppEnvironment.self) private var environment
    #if DEBUG
    @State private var showDesignSystemSheet: Bool = false
    #endif

    public init() {}

    public var body: some View {
        ZStack {
            AppColors.background
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: AppSpacing.large) {
                    // Header Brand
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

                        VStack(spacing: AppSpacing.micro) {
                            Text("MediScanAI")
                                .font(.appLargeTitle)
                                .foregroundColor(AppColors.textPrimary)

                            Text("Authenticated Session Active")
                                .font(.appSubheadline)
                                .foregroundColor(AppColors.textSecondary)
                        }
                    }
                    .padding(.top, AppSpacing.large)

                    // User Profile Card
                    if let user = environment.authManager.currentUser {
                        AppCard {
                            VStack(alignment: .leading, spacing: AppSpacing.standard) {
                                HStack {
                                    VStack(alignment: .leading, spacing: AppSpacing.micro) {
                                        Text(user.fullName ?? "MediScanAI Clinician")
                                            .font(.appHeadline)
                                            .foregroundColor(AppColors.textPrimary)

                                        Text(user.email)
                                            .font(.appBody)
                                            .foregroundColor(AppColors.textSecondary)
                                            .accessibilityIdentifier("AuthenticatedHome_UserEmail")
                                    }

                                    Spacer()

                                    // Active Status Capsule
                                    HStack(spacing: AppSpacing.micro) {
                                        Circle()
                                            .fill(AppColors.statusSuccess)
                                            .frame(width: 8, height: 8)

                                        Text("Active")
                                            .font(.appCaption1)
                                            .fontWeight(.semibold)
                                            .foregroundColor(AppColors.textPrimary)
                                    }
                                    .padding(.horizontal, AppSpacing.compact)
                                    .padding(.vertical, AppSpacing.micro)
                                    .background(AppColors.surfaceTertiary)
                                    .cornerRadius(AppRadius.small)
                                }

                                AppDivider()

                                HStack {
                                    Text("Account ID")
                                        .font(.appCaption1)
                                        .foregroundColor(AppColors.textTertiary)
                                    Spacer()
                                    Text("#\(user.id)")
                                        .font(.appCaption1)
                                        .monospacedDigit()
                                        .foregroundColor(AppColors.textSecondary)
                                }
                            }
                        }
                    }

                    // Informational Banner
                    NoticeBanner(
                        variant: .disclaimer,
                        title: "Phase 4 Authentication Foundation",
                        message: "Secure session restored. Report scanning, clinical analysis, and symptom monitoring features will be activated in Phase 5."
                    )

                    // Sign Out Button
                    AppButton(
                        "Sign Out",
                        icon: "rectangle.portrait.and.arrow.right",
                        variant: .destructive
                    ) {
                        environment.authManager.logout()
                    }
                    .accessibilityIdentifier("AuthenticatedHome_SignOutButton")

                    #if DEBUG
                    SecondaryButton("Explore Design System", icon: "square.grid.2x2") {
                        showDesignSystemSheet = true
                    }
                    .accessibilityIdentifier("ExploreDesignSystemButton_AuthHome")
                    #endif
                }
                .padding(.horizontal, AppSpacing.extraLarge)
                .padding(.bottom, AppSpacing.extraLarge)
            }
        }
        #if DEBUG
        .sheet(isPresented: $showDesignSystemSheet) {
            DesignSystemPreviewView()
        }
        #endif
    }
}
