import Foundation
import Security

// MARK: - Keychain Errors

public enum KeychainError: Error, Equatable, LocalizedError {
    case duplicateItem
    case itemNotFound
    case unhandledStatus(OSStatus)
    case invalidData

    public var errorDescription: String? {
        switch self {
        case .duplicateItem:
            return "Item already exists in Keychain."
        case .itemNotFound:
            return "Item not found in Keychain."
        case .unhandledStatus(let status):
            return "Keychain error status: \(status)"
        case .invalidData:
            return "Unable to decode Keychain data into valid string."
        }
    }
}

// MARK: - Keychain Storage Protocol

public protocol KeychainStorageProtocol: AnyObject {
    func saveToken(_ token: String) throws
    func getToken() throws -> String?
    func deleteToken() throws
}

// MARK: - Native Security Framework Keychain Storage (AUTH-01)

public final class KeychainStorage: KeychainStorageProtocol {
    public let service: String
    public let account: String

    public init(
        service: String = "ai.mediscan.ios.auth",
        account: String = "jwt_access_token"
    ) {
        self.service = service
        self.account = account
    }

    public func saveToken(_ token: String) throws {
        guard let data = token.data(using: .utf8) else {
            throw KeychainError.invalidData
        }

        // Query to check if the token already exists
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let updateAttributes: [String: Any] = [
            kSecValueData as String: data
        ]

        // Attempt update first
        let status = SecItemUpdate(query as CFDictionary, updateAttributes as CFDictionary)

        if status == errSecSuccess {
            return
        } else if status == errSecItemNotFound {
            // Item does not exist; insert as new item
            var newItem = query
            newItem[kSecValueData as String] = data
            // Accessible after first device unlock
            newItem[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock

            let insertStatus = SecItemAdd(newItem as CFDictionary, nil)
            guard insertStatus == errSecSuccess else {
                throw KeychainError.unhandledStatus(insertStatus)
            }
        } else {
            throw KeychainError.unhandledStatus(status)
        }
    }

    public func getToken() throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess else {
            throw KeychainError.unhandledStatus(status)
        }
        guard let data = item as? Data, let token = String(data: data, encoding: .utf8) else {
            throw KeychainError.invalidData
        }

        return token
    }

    public func deleteToken() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let status = SecItemDelete(query as CFDictionary)
        if status == errSecItemNotFound || status == errSecSuccess {
            return
        }
        throw KeychainError.unhandledStatus(status)
    }
}

// MARK: - Mock Keychain Storage (for deterministic unit tests)

public final class MockKeychainStorage: KeychainStorageProtocol {
    private var storage: [String: String] = [:]
    public var shouldThrowError: KeychainError?

    public init(initialToken: String? = nil) {
        if let token = initialToken {
            storage["jwt_access_token"] = token
        }
    }

    public func saveToken(_ token: String) throws {
        if let error = shouldThrowError {
            throw error
        }
        storage["jwt_access_token"] = token
    }

    public func getToken() throws -> String? {
        if let error = shouldThrowError {
            throw error
        }
        return storage["jwt_access_token"]
    }

    public func deleteToken() throws {
        if let error = shouldThrowError {
            throw error
        }
        storage.removeValue(forKey: "jwt_access_token")
    }
}
