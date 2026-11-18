import SwiftUI

/// Main entry point for the native MediScanAI iOS application.
@main
struct MediScanAIApp: App {
    @State private var environment = AppEnvironment()
    @State private var coordinator = AppCoordinator()
    
    var body: some Scene {
        WindowGroup {
            Group {
                #if DEBUG
                if ProcessInfo.processInfo.arguments.contains("-UITest_DesignSystemPreview") || coordinator.currentDestination == .designSystemPreview {
                    DesignSystemPreviewView()
                } else {
                    FoundationLaunchView()
                }
                #else
                FoundationLaunchView()
                #endif
            }
            .environment(environment)
            .environment(coordinator)
            .preferredColorScheme(.dark)
        }
    }
}

/// Intentional foundation screen for Phase 1 & Phase 2.
/// Embodies the true-black monochromatic aesthetic without generic template styling.
struct FoundationLaunchView: View {
    @Environment(AppCoordinator.self) private var coordinator
    @State private var isVisible = false
    #if DEBUG
    @State private var showDesignSystemSheet = false
    #endif
    
    var body: some View {
        ZStack {
            // True OLED black background foundation
            AppColors.background
                .ignoresSafeArea()
            
            VStack(spacing: AppSpacing.extraLarge) {
                Spacer()
                
                // Minimalist monochromatic brand badge
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
                .accessibilityHidden(true)
                
                // Branding & Subtitle
                VStack(spacing: AppSpacing.compact) {
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
                
                Spacer()
                
                #if DEBUG
                // Development-only component library preview trigger button
                SecondaryButton("Explore Design System", icon: "square.grid.2x2") {
                    showDesignSystemSheet = true
                }
                .frame(maxWidth: 260)
                .accessibilityIdentifier("ExploreDesignSystemButton")
                #endif
                
                // Foundation status capsule
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
            .opacity(isVisible ? 1 : 0)
            .scaleEffect(isVisible ? 1 : 0.98)
            .animation(.easeOut(duration: 0.4), value: isVisible)
        }
        .onAppear {
            isVisible = true
        }
        #if DEBUG
        .sheet(isPresented: $showDesignSystemSheet) {
            DesignSystemPreviewView()
        }
        #endif
    }
}

#Preview {
    FoundationLaunchView()
        .environment(AppCoordinator())
        .preferredColorScheme(.dark)
}
