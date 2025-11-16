import Foundation

public protocol SyncProvider {
    func downloadRemoteEntries(token: String) async throws -> [VocabularyEntry]
    func upload(entries: [VocabularyEntry], token: String) async throws
}

public final class GoogleDriveSyncProvider: SyncProvider {
    private let session: URLSession
    private let fileId: String

    public init(fileId: String, session: URLSession = .shared) {
        self.fileId = fileId
        self.session = session
    }

    public func downloadRemoteEntries(token: String) async throws -> [VocabularyEntry] {
        let url = URL(string: "https://www.googleapis.com/drive/v3/files/\(fileId)?alt=media")!
        var request = URLRequest(url: url)
        request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw SyncError.downloadFailed
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([VocabularyEntry].self, from: data)
    }

    public func upload(entries: [VocabularyEntry], token: String) async throws {
        let url = URL(string: "https://www.googleapis.com/upload/drive/v3/files/\(fileId)?uploadType=media")!
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        request.httpBody = try encoder.encode(entries)
        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw SyncError.uploadFailed
        }
    }
}

public enum SyncError: Error, LocalizedError, Equatable {
    case downloadFailed
    case uploadFailed
    case desktopUnavailable

    public var errorDescription: String? {
        switch self {
        case .downloadFailed:
            return "無法從 Google Drive 下載資料。"
        case .uploadFailed:
            return "無法將資料上傳到 Google Drive。"
        case .desktopUnavailable:
            return "桌面版 API 未啟用，已改用本地資料。"
        }
    }
}

public final class DesktopAPIClient {
    private let session: URLSession
    private let baseURL: URL?

    public init(baseURL: URL?, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    public func fetchEntries() async throws -> [VocabularyEntry] {
        guard let baseURL else { throw SyncError.desktopUnavailable }
        let url = baseURL.appending(path: "api/entries")
        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw SyncError.desktopUnavailable
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([VocabularyEntry].self, from: data)
    }

    public func push(entries: [VocabularyEntry]) async throws {
        guard let baseURL else { throw SyncError.desktopUnavailable }
        let url = baseURL.appending(path: "api/entries")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        request.httpBody = try encoder.encode(entries)
        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw SyncError.desktopUnavailable
        }
    }
}

public final class SyncCoordinator {
    private let storage: VocabularyStorage
    private let provider: SyncProvider
    private let merger: VocabularyMerger
    private let desktopClient: DesktopAPIClient?

    public init(storage: VocabularyStorage, provider: SyncProvider, merger: VocabularyMerger = VocabularyMerger(), desktopClient: DesktopAPIClient? = nil) {
        self.storage = storage
        self.provider = provider
        self.merger = merger
        self.desktopClient = desktopClient
    }

    public func performSync(token: String) async -> Result<[VocabularyEntry], Error> {
        do {
            let local = try storage.loadEntries()
            let remote = try await provider.downloadRemoteEntries(token: token)
            let merged = merger.merge(local: local, remote: remote, resolution: .newest)
            try storage.saveEntries(merged)
            try await provider.upload(entries: merged, token: token)
            try await desktopClient?.push(entries: merged)
            return .success(merged)
        } catch {
            return .failure(error)
        }
    }
}
