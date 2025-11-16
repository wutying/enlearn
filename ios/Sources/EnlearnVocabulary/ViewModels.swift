import Foundation
import Combine

@MainActor
public final class WordListViewModel: ObservableObject {
    @Published public private(set) var entries: [VocabularyEntry] = []
    @Published public var searchText: String = ""
    @Published public var reviewMode: ReviewMode = .wordFirst
    private let repository: VocabularyRepositoryProtocol

    public init(repository: VocabularyRepositoryProtocol) {
        self.repository = repository
    }

    public func load() async {
        entries = (try? await repository.fetchEntries()) ?? []
    }

    public func search() async {
        entries = (try? await repository.search(keyword: searchText)) ?? []
    }

    public func toggleMode() {
        reviewMode = reviewMode == .wordFirst ? .definitionFirst : .wordFirst
    }
}

@MainActor
public final class AddWordViewModel: ObservableObject {
    @Published public var word: String = ""
    @Published public var definition: String = ""
    @Published public var context: String = ""
    @Published public private(set) var message: String?
    private let repository: VocabularyRepositoryProtocol

    public init(repository: VocabularyRepositoryProtocol) {
        self.repository = repository
    }

    public func add() async {
        guard !word.isEmpty, !definition.isEmpty else {
            message = "請輸入完整的單字與解釋。"
            return
        }
        do {
            _ = try await repository.add(word: word, definition: definition, context: context.isEmpty ? nil : context)
            message = "已新增 \(word)"
            word = ""
            definition = ""
            context = ""
        } catch {
            message = "新增失敗：\(error.localizedDescription)"
        }
    }
}

@MainActor
public final class ReviewViewModel: ObservableObject {
    @Published public private(set) var queue: [VocabularyEntry] = []
    @Published public private(set) var current: VocabularyEntry?
    private let repository: VocabularyRepositoryProtocol

    public init(repository: VocabularyRepositoryProtocol) {
        self.repository = repository
    }

    public func load(entries: [VocabularyEntry]? = nil) async {
        let items = entries ?? (try? await repository.fetchEntries()) ?? []
        queue = items.shuffled()
        current = queue.first
    }

    public func submit(result: Bool) async {
        guard let current else { return }
        _ = try? await repository.review(result: result, entry: current)
        queue.removeFirst()
        self.current = queue.first
    }
}

@MainActor
public final class SettingsViewModel: ObservableObject {
    @Published public private(set) var settings: Settings
    private let syncCoordinator: SyncCoordinator
    private let tokenProvider: () -> String?

    public init(settings: Settings = Settings(), syncCoordinator: SyncCoordinator, tokenProvider: @escaping () -> String?) {
        self.settings = settings
        self.syncCoordinator = syncCoordinator
        self.tokenProvider = tokenProvider
    }

    public func signIn() {
        settings.isSignedIn = true
    }

    public func signOut() {
        settings.isSignedIn = false
    }

    public func updateFrequency(_ minutes: Int) {
        settings.syncFrequencyMinutes = minutes
        settings.syncStatus.automaticFrequencyMinutes = minutes
    }

    public func triggerSync() async {
        guard let token = tokenProvider() else {
            settings.syncStatus.lastError = "尚未登入 Google 帳戶"
            return
        }
        let result = await syncCoordinator.performSync(token: token)
        switch result {
        case .success:
            settings.syncStatus.lastSyncedAt = Date()
            settings.syncStatus.lastError = nil
        case .failure(let error):
            settings.syncStatus.lastError = error.localizedDescription
        }
    }
}
