import XCTest
import SwiftUI
@testable import MediScanAI

final class DesignSystemTests: XCTestCase {

    // MARK: - Color Token Verification
    func testMonochromaticHexConstants() {
        XCTAssertEqual(AppColors.Hex.background, "#000000")
        XCTAssertEqual(AppColors.Hex.surfacePrimary, "#0A0A0A")
        XCTAssertEqual(AppColors.Hex.surfaceSecondary, "#141414")
        XCTAssertEqual(AppColors.Hex.surfaceTertiary, "#1E1E1E")
        XCTAssertEqual(AppColors.Hex.surfaceElevated, "#262626")
        XCTAssertEqual(AppColors.Hex.borderSubtle, "#2A2A2A")
        XCTAssertEqual(AppColors.Hex.borderFocus, "#404040")
        XCTAssertEqual(AppColors.Hex.textPrimary, "#FFFFFF")
        XCTAssertEqual(AppColors.Hex.textSecondary, "#A1A1A1")
        XCTAssertEqual(AppColors.Hex.textTertiary, "#707070")
        XCTAssertEqual(AppColors.Hex.iconPrimary, "#F5F5F5")
        XCTAssertEqual(AppColors.Hex.iconSecondary, "#929292")
        XCTAssertEqual(AppColors.Hex.accentNeutral, "#FFFFFF")
        XCTAssertEqual(AppColors.Hex.disabled, "#484848")
    }

    func testSemanticStatusHexConstants() {
        // Danger / Acute Emergency
        XCTAssertEqual(AppColors.Hex.statusDanger, "#F43F5E")
        XCTAssertEqual(AppColors.Hex.statusDangerFill, "#2D0A14")
        XCTAssertEqual(AppColors.Hex.statusDangerBorder, "#5C1D2C")

        // Success / Matched Indications
        XCTAssertEqual(AppColors.Hex.statusSuccess, "#10B981")
        XCTAssertEqual(AppColors.Hex.statusSuccessFill, "#06281E")
        XCTAssertEqual(AppColors.Hex.statusSuccessBorder, "#0D5C45")

        // Warning / Caution / Inconclusive
        XCTAssertEqual(AppColors.Hex.statusWarning, "#F59E0B")
        XCTAssertEqual(AppColors.Hex.statusWarningFill, "#2E1E05")
        XCTAssertEqual(AppColors.Hex.statusWarningBorder, "#5C4010")
    }

    func testColorHexParsing() {
        let whiteColor = Color(hex: "#FFFFFF")
        let blackColor = Color(hex: "#000000")
        let shortHex = Color(hex: "#FFF")
        let alphaHex = Color(hex: "#FF000000")
        
        XCTAssertNotNil(whiteColor)
        XCTAssertNotNil(blackColor)
        XCTAssertNotNil(shortHex)
        XCTAssertNotNil(alphaHex)
    }

    // MARK: - Spacing Scale Verification
    func testSpacingScaleConstants() {
        XCTAssertEqual(AppSpacing.micro, 4.0)
        XCTAssertEqual(AppSpacing.compact, 8.0)
        XCTAssertEqual(AppSpacing.small, 12.0)
        XCTAssertEqual(AppSpacing.standard, 16.0)
        XCTAssertEqual(AppSpacing.large, 20.0)
        XCTAssertEqual(AppSpacing.extraLarge, 24.0)
        XCTAssertEqual(AppSpacing.section, 32.0)
        XCTAssertEqual(AppSpacing.clearance, 48.0)
    }

    // MARK: - Corner Radii Scale Verification
    func testCornerRadiiConstants() {
        XCTAssertEqual(AppRadius.small, 8.0)
        XCTAssertEqual(AppRadius.medium, 12.0)
        XCTAssertEqual(AppRadius.large, 16.0)
        XCTAssertEqual(AppRadius.modal, 24.0)
        XCTAssertEqual(AppRadius.pill, 999.0)
    }

    // MARK: - Verdict Status Enum Verification
    func testClinicalVerdictStatusMapping() {
        XCTAssertEqual(ClinicalVerdictStatus.danger.title, "Not Suitable")
        XCTAssertEqual(ClinicalVerdictStatus.danger.defaultIcon, "exclamationmark.octagon.fill")

        XCTAssertEqual(ClinicalVerdictStatus.success.title, "Suitable")
        XCTAssertEqual(ClinicalVerdictStatus.success.defaultIcon, "checkmark.circle.fill")

        XCTAssertEqual(ClinicalVerdictStatus.warning.title, "Caution")
        XCTAssertEqual(ClinicalVerdictStatus.warning.defaultIcon, "exclamationmark.triangle.fill")

        XCTAssertEqual(ClinicalVerdictStatus.neutral.title, "Info")
        XCTAssertEqual(ClinicalVerdictStatus.neutral.defaultIcon, "info.circle.fill")
    }

    // MARK: - Notice Banner Variant Verification
    func testNoticeBannerVariants() {
        let emergency = NoticeBannerVariant.emergency
        XCTAssertEqual(emergency.icon, "phone.fill")
        XCTAssertEqual(emergency.accentColor, AppColors.statusDanger)

        let disclaimer = NoticeBannerVariant.disclaimer
        XCTAssertEqual(disclaimer.icon, "cross.case.fill")
        XCTAssertEqual(disclaimer.accentColor, AppColors.textSecondary)

        let warning = NoticeBannerVariant.warning
        XCTAssertEqual(warning.icon, "exclamationmark.triangle.fill")
        XCTAssertEqual(warning.accentColor, AppColors.statusWarning)
    }

    // MARK: - AppCoordinator Navigation to Preview
    func testAppCoordinatorDesignSystemNavigation() {
        let coordinator = AppCoordinator()
        XCTAssertEqual(coordinator.currentDestination, .foundation)

        coordinator.navigateToDesignSystemPreview()
        XCTAssertEqual(coordinator.currentDestination, .designSystemPreview)

        coordinator.resetToFoundation()
        XCTAssertEqual(coordinator.currentDestination, .foundation)
    }
}
