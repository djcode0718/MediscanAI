import SwiftUI

// MARK: - Dual-Concentric Ring Spinner (StatusIndicator)

public struct StatusIndicator: View {
    public let size: CGFloat
    @State private var isOuterRotating = false
    @State private var isInnerRotating = false
    @State private var isPulsing = false

    public init(size: CGFloat = 64) {
        self.size = size
    }

    public var body: some View {
        ZStack {
            // Subtle breathing glow/pulse background
            Circle()
                .fill(AppColors.textPrimary.opacity(0.04))
                .frame(width: size * 1.3, height: size * 1.3)
                .scaleEffect(isPulsing ? 1.08 : 0.94)

            // Outer ring (clockwise)
            Circle()
                .trim(from: 0.1, to: 0.8)
                .stroke(
                    LinearGradient(
                        colors: [AppColors.textPrimary, AppColors.textPrimary.opacity(0.1)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    style: StrokeStyle(lineWidth: 3, lineCap: .round)
                )
                .frame(width: size, height: size)
                .rotationEffect(.degrees(isOuterRotating ? 360 : 0))

            // Inner ring (counter-clockwise)
            Circle()
                .trim(from: 0.2, to: 0.75)
                .stroke(
                    LinearGradient(
                        colors: [AppColors.textSecondary, AppColors.textTertiary.opacity(0.15)],
                        startPoint: .bottomTrailing,
                        endPoint: .topLeading
                    ),
                    style: StrokeStyle(lineWidth: 2, lineCap: .round)
                )
                .frame(width: size * 0.65, height: size * 0.65)
                .rotationEffect(.degrees(isInnerRotating ? -360 : 0))

            // Center core dot
            Circle()
                .fill(AppColors.textPrimary)
                .frame(width: 6, height: 6)
                .opacity(isPulsing ? 1.0 : 0.5)
        }
        .onAppear {
            withAnimation(
                .linear(duration: 1.8)
                .repeatForever(autoreverses: false)
            ) {
                isOuterRotating = true
            }

            withAnimation(
                .linear(duration: 2.4)
                .repeatForever(autoreverses: false)
            ) {
                isInnerRotating = true
            }

            withAnimation(
                .easeInOut(duration: 1.2)
                .repeatForever(autoreverses: true)
            ) {
                isPulsing = true
            }
        }
    }
}

// MARK: - Staged Inference Loading View

public struct AppStageLoadingView: View {
    public let stageText: String
    public let progress: Double? // 0.0 to 1.0

    public init(stageText: String, progress: Double? = nil) {
        self.stageText = stageText
        self.progress = progress
    }

    public var body: some View {
        VStack(spacing: AppSpacing.large) {
            StatusIndicator(size: 72)

            Text(stageText)
                .font(.appHeadline)
                .foregroundColor(AppColors.textPrimary)
                .multilineTextAlignment(.center)
                .animation(.easeInOut(duration: 0.25), value: stageText)
                .padding(.horizontal, AppSpacing.large)

            if let progress = progress {
                VStack(spacing: AppSpacing.micro) {
                    GeometryReader { geometry in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: AppRadius.pill)
                                .fill(AppColors.surfaceTertiary)
                                .frame(height: 3)

                            RoundedRectangle(cornerRadius: AppRadius.pill)
                                .fill(AppColors.textPrimary)
                                .frame(width: max(0, min(geometry.size.width * CGFloat(progress), geometry.size.width)), height: 3)
                                .animation(.easeOut(duration: 0.3), value: progress)
                        }
                    }
                    .frame(height: 3)
                    .padding(.horizontal, AppSpacing.clearance)

                    Text("\(Int(progress * 100))%")
                        .font(.appFootnote)
                        .foregroundColor(AppColors.textTertiary)
                        .monospacedDigit()
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, AppSpacing.section)
    }
}

// MARK: - Inline / Button Loading Spinner

public struct AppLoadingIndicator: View {
    public let tint: Color
    public let size: CGFloat

    public init(tint: Color = AppColors.textPrimary, size: CGFloat = 20) {
        self.tint = tint
        self.size = size
    }

    public var body: some View {
        ProgressView()
            .progressViewStyle(CircularProgressViewStyle(tint: tint))
            .scaleEffect(size / 20.0)
    }
}
