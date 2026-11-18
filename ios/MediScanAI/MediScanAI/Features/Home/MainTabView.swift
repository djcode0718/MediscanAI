import SwiftUI

// MARK: - Main Tab View (NAV-01)

public struct MainTabView: View {
    @Environment(AppCoordinator.self) private var coordinator
    @Environment(AppEnvironment.self) private var environment

    public init() {
        configureTabBarAppearance()
    }

    public var body: some View {
        @Bindable var coord = coordinator

        TabView(selection: $coord.selectedTab) {
            HomeView(networkClient: environment.networkClient)
                .tabItem {
                    Label(AppTab.home.title, systemImage: AppTab.home.icon)
                }
                .tag(AppTab.home)
                .accessibilityIdentifier("Tab_Home")

            ScanPlaceholderView()
                .tabItem {
                    Label(AppTab.scan.title, systemImage: AppTab.scan.icon)
                }
                .tag(AppTab.scan)
                .accessibilityIdentifier("Tab_Scan")

            HistoryPlaceholderView()
                .tabItem {
                    Label(AppTab.history.title, systemImage: AppTab.history.icon)
                }
                .tag(AppTab.history)
                .accessibilityIdentifier("Tab_History")

            ProfilePlaceholderView()
                .tabItem {
                    Label(AppTab.profile.title, systemImage: AppTab.profile.icon)
                }
                .tag(AppTab.profile)
                .accessibilityIdentifier("Tab_Profile")
        }
        .tint(AppColors.textPrimary)
        .accessibilityIdentifier("MainTabView")
    }

    // MARK: - Monochromatic OLED Tab Bar Styling

    private func configureTabBarAppearance() {
        let appearance = UITabBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = UIColor(AppColors.background)
        appearance.shadowColor = UIColor(AppColors.borderSubtle)

        let inactiveColor = UIColor(red: 0x70 / 255.0, green: 0x70 / 255.0, blue: 0x70 / 255.0, alpha: 1.0)
        let activeColor = UIColor.white

        let itemAppearance = UITabBarItemAppearance()

        // Normal (inactive) state
        itemAppearance.normal.iconColor = inactiveColor
        itemAppearance.normal.titleTextAttributes = [
            .foregroundColor: inactiveColor,
            .font: UIFont.systemFont(ofSize: 10, weight: .medium)
        ]

        // Selected (active) state
        itemAppearance.selected.iconColor = activeColor
        itemAppearance.selected.titleTextAttributes = [
            .foregroundColor: activeColor,
            .font: UIFont.systemFont(ofSize: 10, weight: .semibold)
        ]

        appearance.stackedLayoutAppearance = itemAppearance
        appearance.inlineLayoutAppearance = itemAppearance
        appearance.compactInlineLayoutAppearance = itemAppearance

        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }
}
