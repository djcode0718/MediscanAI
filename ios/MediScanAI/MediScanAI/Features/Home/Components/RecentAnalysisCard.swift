import SwiftUI

// MARK: - AnalysisListItem Convenience Extensions

extension AnalysisListItem {
    public var verdictStatus: ClinicalVerdictStatus {
        guard let v = verdict?.lowercased() else {
            if status.lowercased() == "failed" { return .danger }
            return .neutral
        }
        if v.contains("not suitable") || v.contains("danger") || v.contains("incompatible") || v.contains("hazard") || v.contains("harmful") {
            return .danger
        } else if v.contains("suitable") || v.contains("safe") || v.contains("compatible") || v.contains("approved") {
            return .success
        } else if v.contains("caution") || v.contains("warning") || v.contains("risk") || v.contains("moderate") {
            return .warning
        }
        return .neutral
    }

    public var modalityIcon: String {
        switch modality.uppercased() {
        case "IMAGE": return "camera.fill"
        case "TEXT": return "text.bubble.fill"
        case "AUDIO": return "waveform"
        case "MULTIMODAL": return "sparkles"
        default: return "doc.text.fill"
        }
    }
}

// MARK: - Recent Analysis Card (NAV-04)

public struct RecentAnalysisCard: View {
    public let analysis: AnalysisListItem
    public let onSelect: (AnalysisListItem) -> Void

    public init(
        analysis: AnalysisListItem,
        onSelect: @escaping (AnalysisListItem) -> Void
    ) {
        self.analysis = analysis
        self.onSelect = onSelect
    }

    public var body: some View {
        Button(action: {
            HapticFeedback.shared.impact(.light)
            onSelect(analysis)
        }) {
            AppCard(padding: AppSpacing.standard) {
                VStack(alignment: .leading, spacing: AppSpacing.small) {
                    HStack(alignment: .center, spacing: AppSpacing.compact) {
                        HStack(spacing: AppSpacing.micro + 2) {
                            Image(systemName: analysis.modalityIcon)
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundColor(AppColors.textSecondary)

                            Text(analysis.modality.uppercased())
                                .font(.appCaption2)
                                .fontWeight(.bold)
                                .foregroundColor(AppColors.textSecondary)
                        }
                        .padding(.horizontal, AppSpacing.compact)
                        .padding(.vertical, AppSpacing.micro + 1)
                        .background(AppColors.surfaceTertiary)
                        .cornerRadius(AppRadius.small)

                        Spacer()

                        VerdictBadge(
                            status: analysis.verdictStatus,
                            text: analysis.verdict ?? analysis.status.capitalized
                        )
                    }

                    HStack(alignment: .center) {
                        HStack(spacing: AppSpacing.micro) {
                            Image(systemName: "clock")
                                .font(.system(size: 11))
                                .foregroundColor(AppColors.textTertiary)

                            Text(HomeViewModel.relativeTimestamp(for: analysis.createdAt))
                                .font(.appCaption1)
                                .foregroundColor(AppColors.textSecondary)

                            if let duration = analysis.processingDurationMs {
                                Text("• \(duration)ms")
                                    .font(.appCaption2)
                                    .foregroundColor(AppColors.textTertiary)
                            }
                        }

                        Spacer()

                        Image(systemName: "chevron.right")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(AppColors.textTertiary)
                    }
                }
            }
        }
        .buttonStyle(AppScaleButtonStyle(scaleAmount: 0.99))
        .accessibilityIdentifier("RecentAnalysisCard_\(analysis.id)")
    }
}
