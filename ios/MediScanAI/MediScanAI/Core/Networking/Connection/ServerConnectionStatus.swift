import Foundation

// MARK: - Server Connection Status (WIFI-02, WIFI-03)

/// Represents the reachability and health status of the host backend server.
public enum ServerConnectionStatus: Equatable {
    /// Initial state before any connectivity check has run
    case unknown

    /// Health check probe is actively running
    case checking

    /// Host server is reachable, healthy, and responsive
    case connected(latencyMs: Double)

    /// Host server cannot be reached or returned an error
    case unreachable(reason: String)

    public var isConnected: Bool {
        if case .connected = self { return true }
        return false
    }

    public var isChecking: Bool {
        if case .checking = self { return true }
        return false
    }

    public var statusDescription: String {
        switch self {
        case .unknown:
            return "Unchecked"
        case .checking:
            return "Checking..."
        case .connected(let latency):
            return "Local Wi-Fi (\(Int(latency)) ms)"
        case .unreachable:
            return "Disconnected"
        }
    }
}
