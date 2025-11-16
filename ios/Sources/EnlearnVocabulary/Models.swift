import Foundation

public enum ReviewMode: String, Codable, CaseIterable, Equatable {
    case wordFirst
    case definitionFirst
}

public struct ReviewProgress: Codable, Equatable {
    public var lastReviewedAt: Date?
    public var streak: Int
    public var correctCount: Int
    public var incorrectCount: Int

    public init(lastReviewedAt: Date? = nil, streak: Int = 0, correctCount: Int = 0, incorrectCount: Int = 0) {
        self.lastReviewedAt = lastReviewedAt
        self.streak = streak
        self.correctCount = correctCount
        self.incorrectCount = incorrectCount
    }
}

public struct VocabularyEntry: Codable, Identifiable, Equatable {
    public var id: UUID
    public var word: String
    public var definition: String
    public var context: String?
    public var createdAt: Date
    public var updatedAt: Date
    public var progress: ReviewProgress

    public init(
        id: UUID = UUID(),
        word: String,
        definition: String,
        context: String? = nil,
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        progress: ReviewProgress = ReviewProgress()
    ) {
        self.id = id
        self.word = word
        self.definition = definition
        self.context = context
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.progress = progress
    }
}

public struct SyncStatus: Codable, Equatable {
    public var lastSyncedAt: Date?
    public var lastError: String?
    public var providerDescription: String
    public var automaticFrequencyMinutes: Int

    public init(lastSyncedAt: Date? = nil, lastError: String? = nil, providerDescription: String = "Google Drive", automaticFrequencyMinutes: Int = 60) {
        self.lastSyncedAt = lastSyncedAt
        self.lastError = lastError
        self.providerDescription = providerDescription
        self.automaticFrequencyMinutes = automaticFrequencyMinutes
    }
}

public struct Settings: Codable, Equatable {
    public var isSignedIn: Bool
    public var syncFrequencyMinutes: Int
    public var syncStatus: SyncStatus

    public init(isSignedIn: Bool = false, syncFrequencyMinutes: Int = 60, syncStatus: SyncStatus = SyncStatus()) {
        self.isSignedIn = isSignedIn
        self.syncFrequencyMinutes = syncFrequencyMinutes
        self.syncStatus = syncStatus
    }
}
