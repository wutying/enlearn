import XCTest
@testable import EnlearnVocabulary

final class MergeTests: XCTestCase {
    func testNewestWinsDuringMerge() {
        let now = Date()
        let local = [VocabularyEntry(id: UUID(uuidString: "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF")!, word: "apple", definition: "本地", updatedAt: now)]
        let remote = [VocabularyEntry(id: UUID(uuidString: "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF")!, word: "apple", definition: "遠端", updatedAt: now.addingTimeInterval(60))]
        let merger = VocabularyMerger()

        let merged = merger.merge(local: local, remote: remote, resolution: .newest)

        XCTAssertEqual(merged.count, 1)
        XCTAssertEqual(merged.first?.definition, "遠端")
    }

    func testPreferLocalResolutionKeepsLocalCopy() {
        let local = [VocabularyEntry(word: "book", definition: "local")]
        let remote = [VocabularyEntry(id: local[0].id, word: "book", definition: "remote")]
        let merger = VocabularyMerger()

        let merged = merger.merge(local: local, remote: remote, resolution: .preferLocal)

        XCTAssertEqual(merged.first?.definition, "local")
    }
}
