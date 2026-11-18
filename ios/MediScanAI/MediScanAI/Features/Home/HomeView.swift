import SwiftUI

// MARK: - Home Dashboard View (NAV-02, NAV-03, NAV-04)

public struct HomeView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator

    @State private var viewModel: HomeViewModel
    @State private var isShowingSymptomSheet: Bool = false
    @State private var isShowingVoiceSheet: Bool = false
    @State private var selectedAnalysis: AnalysisListItem? = nil

    public init(networkClient: NetworkClientProtocol) {
        _viewModel = State(initialValue: HomeViewModel(networkClient: networkClient))
    }

    public var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: AppSpacing.section) {
                    headerSection
                    greetingSection
                    quickActionsSection
                    recentActivitySection
                }
                .padding(.horizontal, AppSpacing.large)
                .padding(.top, AppSpacing.compact)
                .padding(.bottom, AppSpacing.large)
            }
            .background(AppColors.background)
            .refreshable {
                await viewModel.loadRecentActivity()
            }
            .task {
                await viewModel.loadRecentActivity()
            }
            .sheet(isPresented: $isShowingSymptomSheet) {
                SymptomComposerPlaceholderSheet()
            }
            .sheet(isPresented: $isShowingVoiceSheet) {
                VoiceRecordingPlaceholderSheet()
            }
            .sheet(item: $selectedAnalysis) { item in
                AnalysisDetailPlaceholderSheet(item: item)
            }
        }
        .accessibilityIdentifier("HomeView")
    }

    // MARK: - Header Section

    private var headerSection: some View {
        HStack(alignment: .center) {
            HStack(spacing: AppSpacing.compact) {
                Image(systemName: "cross.case.fill")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(AppColors.textPrimary)

                Text("MEDISCAN")
                    .font(.appHeadline)
                    .fontWeight(.black)
                    .tracking(2.0)
                    .foregroundColor(AppColors.textPrimary)

                Text("AI")
                    .font(.appCaption2)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.background)
                    .padding(.horizontal, AppSpacing.micro + 2)
                    .padding(.vertical, 2)
                    .background(AppColors.textPrimary)
                    .cornerRadius(AppRadius.micro)
            }
            .accessibilityIdentifier("Home_BrandHeader")

            Spacer()

            ServerConnectionBadge()
                .accessibilityIdentifier("Home_ServerConnectionBadge")
        }
    }

    // MARK: - Greeting Section

    private var greetingSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.micro) {
            Text(greetingTitle)
                .font(.appTitle2)
                .fontWeight(.bold)
                .foregroundColor(AppColors.textPrimary)
                .lineLimit(1)
                .accessibilityIdentifier("Home_GreetingTitle")

            Text("Clinical intelligence & prescription analysis")
                .font(.appSubheadline)
                .foregroundColor(AppColors.textSecondary)
                .accessibilityIdentifier("Home_GreetingSubtitle")
        }
    }

    private var greetingTitle: String {
        if let user = environment.authManager.currentUser {
            if let name = user.fullName, !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return "Welcome, \(name)"
            }
            return "Welcome, \(user.email)"
        }
        return "Welcome to MediScanAI"
    }

    // MARK: - Quick Actions Section (NAV-03)

    private var quickActionsSection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            Text("QUICK ACTIONS")
                .font(.appCaption1)
                .fontWeight(.bold)
                .tracking(1.0)
                .foregroundColor(AppColors.textTertiary)

            // Primary Hero Action: Scan Medicine
            Button(action: {
                HapticFeedback.shared.impact(.medium)
                coordinator.selectTab(.scan)
            }) {
                AppCard(
                    backgroundColor: AppColors.surfaceSecondary,
                    borderColor: AppColors.borderPrimary,
                    padding: AppSpacing.standard
                ) {
                    HStack(spacing: AppSpacing.standard) {
                        ZStack {
                            Circle()
                                .fill(AppColors.surfaceTertiary)
                                .frame(width: 52, height: 52)
                                .overlay(
                                    Circle()
                                        .stroke(AppColors.borderSubtle, lineWidth: 1)
                                )

                            Image(systemName: "camera.viewfinder")
                                .font(.system(size: 24, weight: .semibold))
                                .foregroundColor(AppColors.textPrimary)
                        }

                        VStack(alignment: .leading, spacing: AppSpacing.micro) {
                            HStack {
                                Text("Scan Medicine")
                                    .font(.appHeadline)
                                    .fontWeight(.bold)
                                    .foregroundColor(AppColors.textPrimary)

                                Spacer()

                                Image(systemName: "arrow.right")
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundColor(AppColors.textPrimary)
                            }

                            Text("Scan pill, prescription or packaging for instant AI verification")
                                .font(.appCaption1)
                                .foregroundColor(AppColors.textSecondary)
                                .lineLimit(2)
                                .multilineTextAlignment(.leading)
                        }
                    }
                }
            }
            .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.98))
            .accessibilityIdentifier("Home_ScanMedicineCard")

            // Secondary Actions Grid
            HStack(spacing: AppSpacing.standard) {
                // Enter Symptoms Card
                Button(action: {
                    HapticFeedback.shared.impact(.light)
                    isShowingSymptomSheet = true
                }) {
                    AppCard(
                        backgroundColor: AppColors.surfaceSecondary,
                        padding: AppSpacing.standard
                    ) {
                        VStack(alignment: .leading, spacing: AppSpacing.compact) {
                            Image(systemName: "text.badge.plus")
                                .font(.system(size: 20, weight: .semibold))
                                .foregroundColor(AppColors.textPrimary)

                            VStack(alignment: .leading, spacing: 2) {
                                Text("Enter Symptoms")
                                    .font(.appSubheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(AppColors.textPrimary)

                                Text("Clinical triaging & guidance")
                                    .font(.appCaption2)
                                    .foregroundColor(AppColors.textTertiary)
                                    .lineLimit(1)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.98))
                .accessibilityIdentifier("Home_EnterSymptomsCard")

                // Voice Recording Card
                Button(action: {
                    HapticFeedback.shared.impact(.light)
                    isShowingVoiceSheet = true
                }) {
                    AppCard(
                        backgroundColor: AppColors.surfaceSecondary,
                        padding: AppSpacing.standard
                    ) {
                        VStack(alignment: .leading, spacing: AppSpacing.compact) {
                            Image(systemName: "waveform")
                                .font(.system(size: 20, weight: .semibold))
                                .foregroundColor(AppColors.textPrimary)

                            VStack(alignment: .leading, spacing: 2) {
                                Text("Voice Recording")
                                    .font(.appSubheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(AppColors.textPrimary)

                                Text("Dictate clinical query")
                                    .font(.appCaption2)
                                    .foregroundColor(AppColors.textTertiary)
                                    .lineLimit(1)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.98))
                .accessibilityIdentifier("Home_VoiceRecordingCard")
            }
        }
    }

    // MARK: - Recent Activity Section (NAV-04)

    private var recentActivitySection: some View {
        VStack(alignment: .leading, spacing: AppSpacing.standard) {
            HStack(alignment: .center) {
                Text("RECENT ACTIVITY")
                    .font(.appCaption1)
                    .fontWeight(.bold)
                    .tracking(1.0)
                    .foregroundColor(AppColors.textTertiary)

                Spacer()

                Button(action: {
                    HapticFeedback.shared.impact(.light)
                    coordinator.selectTab(.history)
                }) {
                    HStack(spacing: AppSpacing.micro) {
                        Text("View All")
                            .font(.appCaption1)
                            .fontWeight(.semibold)
                            .foregroundColor(AppColors.textSecondary)

                        Image(systemName: "arrow.right")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(AppColors.textSecondary)
                    }
                }
                .accessibilityIdentifier("Home_ViewAllHistoryButton")
            }

            if viewModel.isLoading && !viewModel.isPopulated {
                HStack(spacing: AppSpacing.compact) {
                    AppLoadingIndicator()
                    Text("Loading recent activity...")
                        .font(.appCaption1)
                        .foregroundColor(AppColors.textSecondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, AppSpacing.large)
                .accessibilityIdentifier("Home_RecentActivityLoading")
            } else if let error = viewModel.errorMessage, !viewModel.isPopulated {
                VStack(spacing: AppSpacing.compact) {
                    NoticeBanner(
                        variant: .warning,
                        title: "Could not load activity",
                        message: error
                    )

                    Button("Retry") {
                        Task {
                            await viewModel.loadRecentActivity()
                        }
                    }
                    .font(.appCaption1)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)
                    .padding(.top, AppSpacing.micro)
                    .accessibilityIdentifier("Home_RecentActivityRetryButton")
                }
                .padding(.vertical, AppSpacing.compact)
            } else if viewModel.isEmpty {
                AppEmptyState(
                    icon: "doc.text.magnifyingglass",
                    title: "Awaiting First Analysis",
                    message: "Scan medication packaging or enter symptoms to create your first clinical report.",
                    actionTitle: "Start First Scan",
                    action: {
                        HapticFeedback.shared.impact(.light)
                        coordinator.selectTab(.scan)
                    }
                )
                .accessibilityIdentifier("Home_RecentActivityEmptyState")
            } else {
                VStack(spacing: AppSpacing.compact) {
                    ForEach(viewModel.recentAnalyses) { analysis in
                        RecentAnalysisCard(
                            analysis: analysis,
                            onSelect: { selected in
                                selectedAnalysis = selected
                            }
                        )
                    }
                }
                .accessibilityIdentifier("Home_RecentAnalysesList")
            }
        }
    }
}
