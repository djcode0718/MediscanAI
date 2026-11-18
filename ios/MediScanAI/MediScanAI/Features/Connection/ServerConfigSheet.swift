import SwiftUI

// MARK: - Server Configuration Sheet (WIFI-01, WIFI-02, WIFI-04)

public struct ServerConfigSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(AppEnvironment.self) private var environment

    @State private var urlString: String = ""
    @State private var validationError: String? = nil
    @State private var showSuccessBanner: Bool = false

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: AppSpacing.large) {
                        // Header Guidance
                        VStack(alignment: .leading, spacing: AppSpacing.compact) {
                            Text("Mac Backend Server")
                                .font(.appTitle2)
                                .foregroundColor(AppColors.textPrimary)

                            Text("Configure the local HTTP address of your persistent MacBook backend server.")
                                .font(.appSubheadline)
                                .foregroundColor(AppColors.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.top, AppSpacing.standard)

                        // URL Input Card
                        AppCard {
                            VStack(alignment: .leading, spacing: AppSpacing.standard) {
                                AppTextField(
                                    title: "Server Base URL",
                                    placeholder: "http://192.168.0.155:8000",
                                    text: $urlString,
                                    leadingIcon: "network",
                                    errorMessage: validationError
                                )
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled(true)
                                .keyboardType(.URL)
                                .accessibilityIdentifier("ServerConfig_URLTextField")
                                .onChange(of: urlString) { _, newValue in
                                    validationError = NetworkConfiguration.validationError(for: newValue)
                                }

                                HStack(spacing: AppSpacing.standard) {
                                    // Save Button
                                    PrimaryButton(
                                        "Save & Apply",
                                        icon: "checkmark",
                                        isLoading: false,
                                        isEnabled: validationError == nil && !urlString.isEmpty
                                    ) {
                                        applyURL()
                                    }
                                    .accessibilityIdentifier("ServerConfig_SaveButton")

                                    // Reset Button
                                    SecondaryButton("Reset", icon: "arrow.counterclockwise") {
                                        resetDefault()
                                    }
                                    .accessibilityIdentifier("ServerConfig_ResetButton")
                                }
                            }
                        }

                        // Live Connection Probe Card (WIFI-02)
                        AppCard {
                            VStack(alignment: .leading, spacing: AppSpacing.standard) {
                                HStack {
                                    VStack(alignment: .leading, spacing: AppSpacing.micro) {
                                        Text("Connection Probe")
                                            .font(.appHeadline)
                                            .foregroundColor(AppColors.textPrimary)

                                        Text("Pings GET /api/health to measure round-trip latency.")
                                            .font(.appCaption1)
                                            .foregroundColor(AppColors.textTertiary)
                                    }

                                    Spacer()

                                    // Status Pill
                                    connectionStatusBadge
                                }

                                AppDivider()

                                // Result Feedback
                                probeResultView

                                // Test Button
                                SecondaryButton(
                                    "Test Connection",
                                    icon: "waveform.path.ecg",
                                    isLoading: environment.serverConnectionManager.isTesting
                                ) {
                                    Task {
                                        await environment.serverConnectionManager.checkConnection()
                                    }
                                }
                                .accessibilityIdentifier("ServerConfig_TestButton")
                            }
                        }

                        // Setup Instructions & Wi-Fi Details Card (WIFI-01, WIFI-04)
                        AppCard {
                            VStack(alignment: .leading, spacing: AppSpacing.standard) {
                                HStack(spacing: AppSpacing.compact) {
                                    Image(systemName: "wifi")
                                        .font(.system(size: 16, weight: .semibold))
                                        .foregroundColor(AppColors.textPrimary)

                                    Text("Wi-Fi Setup Instructions")
                                        .font(.appHeadline)
                                        .foregroundColor(AppColors.textPrimary)
                                }

                                VStack(alignment: .leading, spacing: AppSpacing.small) {
                                    instructionRow(
                                        number: "1",
                                        title: "Same Wi-Fi Network",
                                        detail: "Your iPhone and MacBook Air must be connected to the exact same Wi-Fi router or subnet."
                                    )

                                    instructionRow(
                                        number: "2",
                                        title: "Locate Mac LAN IP",
                                        detail: "On your Mac, check System Settings → Wi-Fi → Details, or run `ipconfig getifaddr en0` in Terminal."
                                    )

                                    instructionRow(
                                        number: "3",
                                        title: "Backend Port 8000",
                                        detail: "Ensure the FastAPI backend server is running (`uvicorn backend.main:app --host 0.0.0.0 --port 8000`)."
                                    )

                                    instructionRow(
                                        number: "4",
                                        title: "Local Network Permission",
                                        detail: "iOS requires 'Local Network' permission to reach local hosts. If blocked, check iOS Settings → MediScanAI."
                                    )
                                }
                            }
                        }
                    }
                    .padding(.horizontal, AppSpacing.extraLarge)
                    .padding(.bottom, AppSpacing.extraLarge)
                }
            }
            .navigationTitle("Server Configuration")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.textPrimary)
                    .accessibilityIdentifier("ServerConfig_DoneButton")
                }
            }
            .onAppear {
                urlString = environment.networkConfiguration.baseURL.absoluteString
                validationError = NetworkConfiguration.validationError(for: urlString)
            }
        }
    }

    // MARK: - Subviews

    @ViewBuilder
    private var connectionStatusBadge: some View {
        let status = environment.serverConnectionManager.status
        HStack(spacing: AppSpacing.micro) {
            Circle()
                .fill(badgeColor(for: status))
                .frame(width: 8, height: 8)

            Text(badgeText(for: status))
                .font(.appCaption1)
                .fontWeight(.semibold)
                .foregroundColor(AppColors.textPrimary)
        }
        .padding(.horizontal, AppSpacing.compact)
        .padding(.vertical, AppSpacing.micro)
        .background(AppColors.surfaceTertiary)
        .cornerRadius(AppRadius.small)
        .accessibilityIdentifier("ServerConfig_StatusPill")
    }

    @ViewBuilder
    private var probeResultView: some View {
        switch environment.serverConnectionManager.status {
        case .unknown:
            HStack(spacing: AppSpacing.compact) {
                Image(systemName: "questionmark.circle")
                    .foregroundColor(AppColors.textTertiary)
                Text("Connection has not been tested yet.")
                    .font(.appSubheadline)
                    .foregroundColor(AppColors.textTertiary)
            }

        case .checking:
            HStack(spacing: AppSpacing.compact) {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: AppColors.textPrimary))
                    .scaleEffect(0.8)
                Text("Pinging Mac backend at \(environment.networkConfiguration.baseURL.absoluteString)...")
                    .font(.appSubheadline)
                    .foregroundColor(AppColors.textSecondary)
            }

        case .connected(let latencyMs):
            NoticeBanner(
                variant: .disclaimer,
                title: "Connected to Mac Backend",
                message: "Round-trip health latency: \(Int(latencyMs)) ms. Server is active and accepting requests."
            )
            .accessibilityIdentifier("ServerConfig_SuccessBanner")

        case .unreachable(let reason):
            NoticeBanner(
                variant: .warning,
                title: "Server Unreachable",
                message: reason
            )
            .accessibilityIdentifier("ServerConfig_FailureBanner")
        }
    }

    private func instructionRow(number: String, title: String, detail: String) -> some View {
        HStack(alignment: .top, spacing: AppSpacing.standard) {
            ZStack {
                Circle()
                    .fill(AppColors.surfaceTertiary)
                    .frame(width: 22, height: 22)
                Text(number)
                    .font(.appCaption1)
                    .fontWeight(.bold)
                    .foregroundColor(AppColors.textPrimary)
            }
            .padding(.top, 2)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.appSubheadline)
                    .fontWeight(.semibold)
                    .foregroundColor(AppColors.textPrimary)

                Text(detail)
                    .font(.appFootnote)
                    .foregroundColor(AppColors.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    // MARK: - Actions

    private func applyURL() {
        guard let url = URL(string: urlString.trimmingCharacters(in: .whitespacesAndNewlines)),
              NetworkConfiguration.isValid(url: url) else {
            validationError = "Please enter a valid HTTP/HTTPS URL."
            return
        }

        Task {
            _ = await environment.serverConnectionManager.updateServerURL(url)
            urlString = environment.networkConfiguration.baseURL.absoluteString
        }
    }

    private func resetDefault() {
        Task {
            await environment.serverConnectionManager.resetToDefault()
            urlString = environment.networkConfiguration.baseURL.absoluteString
            validationError = nil
        }
    }

    private func badgeColor(for status: ServerConnectionStatus) -> Color {
        switch status {
        case .connected:
            return AppColors.statusSuccess
        case .unreachable:
            return AppColors.statusDanger
        case .checking:
            return AppColors.statusWarning
        case .unknown:
            return AppColors.textTertiary
        }
    }

    private func badgeText(for status: ServerConnectionStatus) -> String {
        switch status {
        case .connected(let latency):
            return "\(Int(latency)) ms"
        case .unreachable:
            return "Offline"
        case .checking:
            return "Testing..."
        case .unknown:
            return "Unchecked"
        }
    }
}
