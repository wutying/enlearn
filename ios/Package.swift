// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EnlearnVocabulary",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v16)
    ],
    products: [
        .library(name: "EnlearnVocabulary", targets: ["EnlearnVocabulary"])
    ],
    targets: [
        .target(
            name: "EnlearnVocabulary",
            resources: [.process("Resources")]
        ),
        .testTarget(
            name: "EnlearnVocabularyTests",
            dependencies: ["EnlearnVocabulary"]
        )
    ]
)
