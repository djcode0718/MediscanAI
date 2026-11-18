import SwiftUI

// MARK: - App Text Field (Single Line)

public struct AppTextField: View {
    public let title: String?
    public let placeholder: String
    @Binding public var text: String
    public let leadingIcon: String?
    public let isSecure: Bool
    public let errorMessage: String?
    @FocusState private var isFocused: Bool
    @State private var isPasswordVisible: Bool = false

    public init(
        title: String? = nil,
        placeholder: String,
        text: Binding<String>,
        leadingIcon: String? = nil,
        isSecure: Bool = false,
        errorMessage: String? = nil
    ) {
        self.title = title
        self.placeholder = placeholder
        self._text = text
        self.leadingIcon = leadingIcon
        self.isSecure = isSecure
        self.errorMessage = errorMessage
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.compact) {
            if let title = title {
                Text(title)
                    .font(.appSubheadline)
                    .foregroundColor(AppColors.textSecondary)
            }

            HStack(spacing: AppSpacing.compact) {
                if let leadingIcon = leadingIcon {
                    Image(systemName: leadingIcon)
                        .font(.system(size: 16))
                        .foregroundColor(isFocused ? AppColors.iconPrimary : AppColors.iconSecondary)
                }

                if isSecure && !isPasswordVisible {
                    SecureField(
                        "",
                        text: $text,
                        prompt: Text(placeholder).foregroundColor(AppColors.textTertiary)
                    )
                    .focused($isFocused)
                    .foregroundColor(AppColors.textPrimary)
                    .font(.appBody)
                } else {
                    TextField(
                        "",
                        text: $text,
                        prompt: Text(placeholder).foregroundColor(AppColors.textTertiary)
                    )
                    .focused($isFocused)
                    .foregroundColor(AppColors.textPrimary)
                    .font(.appBody)
                }

                if isSecure {
                    Button(action: {
                        isPasswordVisible.toggle()
                        HapticFeedback.shared.impact(.light)
                    }) {
                        Image(systemName: isPasswordVisible ? "eye.slash.fill" : "eye.fill")
                            .font(.system(size: 15))
                            .foregroundColor(AppColors.iconSecondary)
                    }
                } else if !text.isEmpty {
                    Button(action: {
                        text = ""
                        HapticFeedback.shared.impact(.light)
                    }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 15))
                            .foregroundColor(AppColors.iconSecondary)
                    }
                }
            }
            .padding(.horizontal, AppSpacing.standard)
            .frame(height: 50)
            .background(AppColors.surfaceSecondary)
            .cornerRadius(AppRadius.medium)
            .overlay(
                RoundedRectangle(cornerRadius: AppRadius.medium)
                    .stroke(borderColor, lineWidth: isFocused ? 1.5 : 1)
            )

            if let errorMessage = errorMessage, !errorMessage.isEmpty {
                HStack(spacing: AppSpacing.micro) {
                    Image(systemName: "exclamationmark.circle.fill")
                        .font(.system(size: 12))
                    Text(errorMessage)
                        .font(.appCaption1)
                }
                .foregroundColor(AppColors.statusDanger)
                .transition(.opacity)
            }
        }
    }

    private var borderColor: Color {
        if errorMessage != nil && !(errorMessage?.isEmpty ?? true) {
            return AppColors.statusDanger
        }
        if isFocused {
            return AppColors.borderFocus
        }
        return AppColors.borderSubtle
    }
}

// MARK: - App Multiline Input Field (Spacious Text Area)

public struct AppTextEditor: View {
    public let title: String?
    public let placeholder: String
    @Binding public var text: String
    public let minHeight: CGFloat
    public let errorMessage: String?
    @FocusState private var isFocused: Bool

    public init(
        title: String? = nil,
        placeholder: String,
        text: Binding<String>,
        minHeight: CGFloat = 120,
        errorMessage: String? = nil
    ) {
        self.title = title
        self.placeholder = placeholder
        self._text = text
        self.minHeight = minHeight
        self.errorMessage = errorMessage
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.compact) {
            if let title = title {
                Text(title)
                    .font(.appSubheadline)
                    .foregroundColor(AppColors.textSecondary)
            }

            ZStack(alignment: .topLeading) {
                if text.isEmpty {
                    Text(placeholder)
                        .font(.appBody)
                        .foregroundColor(AppColors.textTertiary)
                        .padding(.horizontal, AppSpacing.standard)
                        .padding(.vertical, AppSpacing.small)
                }

                TextEditor(text: $text)
                    .focused($isFocused)
                    .font(.appBody)
                    .foregroundColor(AppColors.textPrimary)
                    .scrollContentBackground(.hidden)
                    .padding(.horizontal, AppSpacing.small)
                    .padding(.vertical, AppSpacing.micro)
                    .frame(minHeight: minHeight)
            }
            .background(AppColors.surfaceSecondary)
            .cornerRadius(AppRadius.medium)
            .overlay(
                RoundedRectangle(cornerRadius: AppRadius.medium)
                    .stroke(borderColor, lineWidth: isFocused ? 1.5 : 1)
            )

            if let errorMessage = errorMessage, !errorMessage.isEmpty {
                HStack(spacing: AppSpacing.micro) {
                    Image(systemName: "exclamationmark.circle.fill")
                        .font(.system(size: 12))
                    Text(errorMessage)
                        .font(.appCaption1)
                }
                .foregroundColor(AppColors.statusDanger)
            }
        }
    }

    private var borderColor: Color {
        if errorMessage != nil && !(errorMessage?.isEmpty ?? true) {
            return AppColors.statusDanger
        }
        if isFocused {
            return AppColors.borderFocus
        }
        return AppColors.borderSubtle
    }
}

// MARK: - Aliases for spec naming
public typealias TextInputField = AppTextField
public typealias MultilineInputField = AppTextEditor
