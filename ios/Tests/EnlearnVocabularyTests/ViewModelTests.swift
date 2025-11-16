import XCTest
@testable import EnlearnVocabulary

final class ViewModelTests: XCTestCase {
    actor InMemoryStorage: VocabularyStorage {
        var items: [VocabularyEntry] = []
        func loadEntries() throws -> [VocabularyEntry] { items }
        func saveEntries(_ entries: [VocabularyEntry]) throws { items = entries }
    }

    func testAddFlowUpdatesList() async {
        let storage = InMemoryStorage()
        let repository = VocabularyRepository(storage: storage)
        let addVM = AddWordViewModel(repository: repository)
        let listVM = WordListViewModel(repository: repository)

        addVM.word = "river"
        addVM.definition = "河流"
        await addVM.add()
        await listVM.load()

        XCTAssertEqual(listVM.entries.count, 1)
        XCTAssertEqual(listVM.entries.first?.word, "river")
    }

    func testReviewModeToggle() {
        let storage = InMemoryStorage()
        let repository = VocabularyRepository(storage: storage)
        let listVM = WordListViewModel(repository: repository)

        XCTAssertEqual(listVM.reviewMode, .wordFirst)
        listVM.toggleMode()
        XCTAssertEqual(listVM.reviewMode, .definitionFirst)
    }

    func testReviewFlowAdvancesQueue() async {
        let storage = InMemoryStorage()
        storage.items = [VocabularyEntry(word: "sun", definition: "太陽"), VocabularyEntry(word: "moon", definition: "月亮")]
        let repository = VocabularyRepository(storage: storage)
        let reviewVM = ReviewViewModel(repository: repository)

        await reviewVM.load()
        let first = reviewVM.current
        await reviewVM.submit(result: true)

        XCTAssertNotEqual(reviewVM.current?.id, first?.id)
    }
}
