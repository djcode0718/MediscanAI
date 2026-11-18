import Foundation
import Network

// MARK: - Network Monitor Protocol

public protocol NetworkMonitoring: AnyObject {
    var isConnected: Bool { get }
    var isWiFi: Bool { get }
    var isCellular: Bool { get }
    var connectionDescription: String { get }

    func start()
    func stop()
}

// MARK: - Native NWPathMonitor Network Monitor

@Observable
public final class NetworkMonitor: NetworkMonitoring {
    public var isConnected: Bool = true
    public var isWiFi: Bool = false
    public var isCellular: Bool = false

    public var connectionDescription: String {
        if !isConnected {
            return "No Connection"
        }
        if isWiFi {
            return "Local Wi-Fi"
        }
        if isCellular {
            return "Cellular"
        }
        return "Connected"
    }

    private let monitor: NWPathMonitor
    private let queue = DispatchQueue(label: "ai.mediscan.network.monitor", qos: .utility)
    private var isStarted = false

    public init() {
        self.monitor = NWPathMonitor()
    }

    public func start() {
        guard !isStarted else { return }
        isStarted = true

        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor [weak self] in
                guard let self = self else { return }
                self.isConnected = (path.status == .satisfied)
                self.isWiFi = path.usesInterfaceType(.wifi)
                self.isCellular = path.usesInterfaceType(.cellular)
            }
        }
        monitor.start(queue: queue)
    }

    public func stop() {
        guard isStarted else { return }
        monitor.cancel()
        isStarted = false
    }

    deinit {
        stop()
    }
}
