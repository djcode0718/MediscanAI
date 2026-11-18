import SwiftUI

// MARK: - Analysis Detail Placeholder Sheet (NAV-04)

public struct AnalysisDetailPlaceholderSheet: View {
    @Environment(\.dismiss) private var dismiss
    public let item: AnalysisListItem

    public init(item: AnalysisListItem) {
        self.item = item
    }

    public var body: some View {
        NavigationStack {
            ZStack {
                AppColors.background
                    .ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: AppSpacing.large) {
                        AppCard {
                            VStack(alignment: .leading, spacing: AppSpacing.standard) {
                                HStack {
                                    Text("Analysis #\(item.id)")
                                        .font(.appHeadline)
                                        .foregroundColor(AppColors.textPrimary)

                                    Spacer()

                                    Text(item.modality.uppercased())
                                        .font(.appCaption2)
                                        .fontWeight(.bold)
                                        .foregroundColor(AppColors.textPrimary)
                                        .padding(.horizontal, AppSpacing.compact)
                                        .padding(.vertical, AppSpacing.micro)
                                        .background(AppColors.surfaceTertiary)
                                        .cornerRadius(AppRadius.small)
                                }

                                AppDivider()

                                if let verdict = item.verdict {
                                    HStack {
                                        Text("Clinical Verdict")
                                            .font(.appSubheadline)
                                            .foregroundColor(AppColors.textSecondary)
                                        Spacer()
                                        Text(verdict.capitalized)
                                            .font(.appSubheadline)
                                            .fontWeight(.semibold)
                                            .foregroundColor(AppColors.textPrimary)
                                    }
                                }

                                HStack {
                                    Text("Recorded Date")
                                        .font(.appSubheadline)
                                        .foregroundColor(AppColors.textSecondary)
                                    Spacer()
                                    Text(item.createdAt.formatted(date: .abbreviated, time: .shortened))
                                        .font(.appFootnote)
                                        .foregroundColor(AppColors.textTertiary)
                                }

                                if let duration = item.processingDurationMs {
                                    HStack {
                                        Text("Inference Latency")
                                            .font(.appSubheadline)
                                            .foregroundColor(AppColors.textSecondary)
                                        Spacer()
                                        Text("\(duration) ms")
                                            .font(.appFootnote)
                                            .monospacedDigit()
                                            .foregroundColor(AppColors.textTertiary)
                                    }
                                }
                            }
                        }

                        NoticeBanner(
                            variant: .disclaimer,
                            title: "Comprehensive Report Placeholder",
                            message: "Detailed multimodal OCR overlays, RAG drug interaction citations, and safety warnings will be activated in Phase 9."
                        )

                        Spacer()
                    }
                    .padding(AppSpacing.extraLarge)
                }
            }
            .navigationTitle("Analysis Record")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(AppColors.textPrimary)
                    .accessibilityIdentifier("AnalysisDetail_DoneButton")
                }
            }
        }
        .accessibilityIdentifier("AnalysisDetailPlaceholderSheet")
    }
}
