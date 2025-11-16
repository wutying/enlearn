import Foundation

public protocol VocabularyRepositoryProtocol {
    func fetchEntries() async throws -> [VocabularyEntry]
    func add(word: String, definition: String, context: String?) async throws -> [VocabularyEntry]
    func update(_ entry: VocabularyEntry) async throws -> [VocabularyEntry]
    func search(keyword: String) async throws -> [VocabularyEntry]
    func review(result: Bool, entry: VocabularyEntry) async throws -> [VocabularyEntry]
}

public final class VocabularyRepository: VocabularyRepositoryProtocol {
    private let storage: VocabularyStorage
    private let desktopClient: DesktopAPIClient?

    public init(storage: VocabularyStorage, desktopClient: DesktopAPIClient? = nil) {
        self.storage = storage
        self.desktopClient = desktopClient
    }

    public func fetchEntries() async throws -> [VocabularyEntry] {
        if let desktopClient, let entries = try? await desktopClient.fetchEntries() {
            try storage.saveEntries(entries)
            return entries
        }
        return try storage.loadEntries()
    }

    public func add(word: String, definition: String, context: String?) async throws -> [VocabularyEntry] {
        var entries = try await fetchEntries()
        let newEntry = VocabularyEntry(word: word, definition: definition, context: context)
        entries.append(newEntry)
        try storage.saveEntries(entries)
        try await desktopClient?.push(entries: entries)
        return entries
    }

    public func update(_ entry: VocabularyEntry) async throws -> [VocabularyEntry] {
        var entries = try await fetchEntries()
        if let index = entries.firstIndex(where: { $0.id == entry.id }) {
            entries[index] = entry
        } else {
            entries.append(entry)
        }
        try storage.saveEntries(entries)
        try await desktopClient?.push(entries: entries)
        return entries
    }

    public func search(keyword: String) async throws -> [VocabularyEntry] {
        guard !keyword.isEmpty else { return try await fetchEntries() }
        let lowercased = keyword.lowercased()
        let entries = try await fetchEntries()
        return entries.filter { $0.word.lowercased().contains(lowercased) || $0.definition.lowercased().contains(lowercased) }
    }

    public func review(result: Bool, entry: VocabularyEntry) async throws -> [VocabularyEntry] {
        var updated = entry
        var progress = updated.progress
        progress.lastReviewedAt = Date()
        if result {
            progress.streak += 1
            progress.correctCount += 1
        } else {
            progress.streak = 0
            progress.incorrectCount += 1
        }
        updated.progress = progress
        updated.updatedAt = Date()
        return try await update(updated)
    }
}
