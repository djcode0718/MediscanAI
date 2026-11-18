import SwiftUI

// MARK: - Profile Tab Placeholder (Phase 6 Placeholder for Phase 10)

public struct ProfilePlaceholderView: View {
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
                    // Header with Connection Badge
                    HStack {
                        VStack(alignment: .leading, spacing: AppSpacing.micro) {
                            Text("Clinician Profile")
                                .font(.appTitle2)
                                .foregroundColor(AppColors.textPrimary)

                            Text("Authenticated credentials & settings")
                                .font(.appCaption1)
                                .foregroundColor(AppColors.textSecondary)
                        }

                        Spacer()

                        ServerConnectionBadge()
                    }
                    .padding(.top, AppSpacing.standard)

                    // User Identity Card
                    if let user = environment.authManager.currentUser {
                        AppCard {
                            VStack(alignment: .leading, spacing: AppSpacing.standard) {
                                HStack(spacing: AppSpacing.standard) {
                                    ZStack {
                                        Circle()
                                            .fill(AppColors.surfaceTertiary)
                                            .frame(width: 52, height: 52)
                                            .overlay(
                                                Circle()
                                                    .stroke(AppColors.borderSubtle, lineWidth: 1)
                                            )

                                        Image(systemName: "person.fill")
                                            .font(.system(size: 24))
                                            .foregroundColor(AppColors.textPrimary)
                                    }

                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(user.fullName ?? "MediScanAI Clinician")
                                            .font(.appHeadline)
                                            .foregroundColor(AppColors.textPrimary)

                                        Text(user.email)
                                            .font(.appBody)
                                            .foregroundColor(AppColors.textSecondary)
                                            .accessibilityIdentifier("Profile_UserEmail")
                                    }

                                    Spacer()
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

                                HStack {
                                    Text("Account Status")
                                        .font(.appCaption1)
                                        .foregroundColor(AppColors.textTertiary)
                                    Spacer()
                                    HStack(spacing: AppSpacing.micro) {
                                        Circle()
                                            .fill(AppColors.statusSuccess)
                                            .frame(width: 6, height: 6)
                                        Text(user.isActive ? "Active Session" : "Inactive")
                                            .font(.appCaption1)
                                            .foregroundColor(AppColors.textSecondary)
                                    }
                                }
                            }
                        }
                    }

                    // Sign Out Action Card
                    AppButton(
                        "Sign Out",
                        icon: "rectangle.portrait.and.arrow.right",
                        variant: .destructive
                    ) {
                        environment.authManager.logout()
                    }
                    .accessibilityIdentifier("Profile_SignOutButton")

                    #if DEBUG
                    SecondaryButton("Explore Design System", icon: "square.grid.2x2") {
                        showDesignSystemSheet = true
                    }
                    .accessibilityIdentifier("ExploreDesignSystemButton_Profile")
                    #endif

                    // Roadmap Phase Capsule
                    HStack(spacing: AppSpacing.compact) {
                        Circle()
                            .fill(AppColors.statusSuccess)
                            .frame(width: 6, height: 6)

                        Text("Phase 10 · Clinician Profile & Settings")
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
                    .padding(.top, AppSpacing.standard)
                }
                .padding(.horizontal, AppSpacing.extraLarge)
                .padding(.bottom, AppSpacing.extraLarge)
            }
        }
        .accessibilityIdentifier("ProfilePlaceholderView")
        #if DEBUG
        .sheet(isPresented: $showDesignSystemSheet) {
            DesignSystemPreviewView()
        }
        #endif
    }
}
