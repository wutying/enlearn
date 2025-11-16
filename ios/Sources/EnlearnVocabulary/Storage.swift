import Foundation

public protocol VocabularyStorage {
    func loadEntries() throws -> [VocabularyEntry]
    func saveEntries(_ entries: [VocabularyEntry]) throws
}

public final class JSONVocabularyStorage: VocabularyStorage {
    private let fileURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.encoder = JSONEncoder()
        self.encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        self.encoder.dateEncodingStrategy = .iso8601
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
    }

    public func loadEntries() throws -> [VocabularyEntry] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return [] }
        let data = try Data(contentsOf: fileURL)
        return try decoder.decode([VocabularyEntry].self, from: data)
    }

    public func saveEntries(_ entries: [VocabularyEntry]) throws {
        let data = try encoder.encode(entries)
        let directory = fileURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try data.write(to: fileURL, options: [.atomic])
    }
}

public enum MergeResolution {
    case preferLocal
    case preferRemote
    case newest
}

public struct VocabularyMerger {
    public init() {}

    public func merge(local: [VocabularyEntry], remote: [VocabularyEntry], resolution: MergeResolution = .newest) -> [VocabularyEntry] {
        var combined: [UUID: VocabularyEntry] = [:]

        for entry in local { combined[entry.id] = entry }

        for remoteEntry in remote {
            if let existing = combined[remoteEntry.id] {
                combined[remoteEntry.id] = resolve(existing: existing, incoming: remoteEntry, strategy: resolution)
            } else {
                combined[remoteEntry.id] = remoteEntry
            }
        }
        return combined.values.sorted { $0.word.lowercased() < $1.word.lowercased() }
    }

    private func resolve(existing: VocabularyEntry, incoming: VocabularyEntry, strategy: MergeResolution) -> VocabularyEntry {
        switch strategy {
        case .preferLocal:
            return existing
        case .preferRemote:
            return incoming
        case .newest:
            return existing.updatedAt >= incoming.updatedAt ? existing : incoming
        }
    }
}
