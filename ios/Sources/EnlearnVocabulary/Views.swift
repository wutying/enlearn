import SwiftUI

public struct ContentView: View {
    @StateObject private var listViewModel: WordListViewModel
    @StateObject private var addViewModel: AddWordViewModel
    @StateObject private var reviewViewModel: ReviewViewModel
    @StateObject private var settingsViewModel: SettingsViewModel

    public init(
        listViewModel: WordListViewModel,
        addViewModel: AddWordViewModel,
        reviewViewModel: ReviewViewModel,
        settingsViewModel: SettingsViewModel
    ) {
        _listViewModel = StateObject(wrappedValue: listViewModel)
        _addViewModel = StateObject(wrappedValue: addViewModel)
        _reviewViewModel = StateObject(wrappedValue: reviewViewModel)
        _settingsViewModel = StateObject(wrappedValue: settingsViewModel)
    }

    public var body: some View {
        TabView {
            NavigationStack {
                WordListView(viewModel: listViewModel)
                    .navigationTitle("單字列表")
                    .toolbar {
                        Button(action: listViewModel.toggleMode) {
                            Label(listViewModel.reviewMode == .wordFirst ? "顯示單字" : "顯示解釋", systemImage: "arrow.triangle.2.circlepath")
                        }
                    }
            }
            .tabItem { Label("列表", systemImage: "list.bullet") }

            NavigationStack {
                AddWordView(viewModel: addViewModel)
                    .navigationTitle("搜尋/新增")
            }
            .tabItem { Label("新增", systemImage: "plus.circle") }

            NavigationStack {
                ReviewView(viewModel: reviewViewModel, mode: $listViewModel.reviewMode)
                    .navigationTitle("複習")
            }
            .tabItem { Label("複習", systemImage: "graduationcap") }

            NavigationStack {
                SettingsView(viewModel: settingsViewModel)
                    .navigationTitle("設定")
            }
            .tabItem { Label("設定", systemImage: "gear") }
        }
        .task { await listViewModel.load() }
    }
}

struct WordListView: View {
    @ObservedObject var viewModel: WordListViewModel

    var body: some View {
        VStack {
            TextField("搜尋單字或解釋", text: $viewModel.searchText)
                .textFieldStyle(.roundedBorder)
                .padding()
                .onSubmit { Task { await viewModel.search() } }

            Picker("複習模式", selection: $viewModel.reviewMode) {
                ForEach(ReviewMode.allCases, id: \.self) { mode in
                    Text(mode == .wordFirst ? "單字猜解釋" : "解釋猜單字").tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)

            List(viewModel.entries) { entry in
                VStack(alignment: .leading, spacing: 6) {
                    Text(entry.word).font(.headline)
                    Text(entry.definition).font(.subheadline)
                    if let context = entry.context, !context.isEmpty {
                        Text(context).font(.footnote).foregroundStyle(.secondary)
                    }
                    HStack {
                        Label("連勝: \(entry.progress.streak)", systemImage: "flame.fill")
                        Label("正確: \(entry.progress.correctCount)", systemImage: "checkmark.circle")
                        Label("錯誤: \(entry.progress.incorrectCount)", systemImage: "xmark.circle")
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            }
        }
    }
}

struct AddWordView: View {
    @ObservedObject var viewModel: AddWordViewModel

    var body: some View {
        Form {
            Section(header: Text("單字")) {
                TextField("輸入單字", text: $viewModel.word)
            }
            Section(header: Text("解釋")) {
                TextField("輸入解釋", text: $viewModel.definition)
            }
            Section(header: Text("例句/備註")) {
                TextField("可選填", text: $viewModel.context)
            }
            Section {
                Button(action: { Task { await viewModel.add() } }) {
                    Label("新增單字", systemImage: "plus")
                }
            }
            if let message = viewModel.message {
                Section {
                    Text(message)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

struct ReviewView: View {
    @ObservedObject var viewModel: ReviewViewModel
    @Binding var mode: ReviewMode

    var body: some View {
        VStack(spacing: 24) {
            Picker("模式", selection: $mode) {
                Text("單字猜解釋").tag(ReviewMode.wordFirst)
                Text("解釋猜單字").tag(ReviewMode.definitionFirst)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)

            if let current = viewModel.current {
                VStack(spacing: 12) {
                    Text(mode == .wordFirst ? current.word : current.definition)
                        .font(.largeTitle)
                        .bold()
                        .multilineTextAlignment(.center)
                    if mode == .definitionFirst {
                        Text(current.word)
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                    if let context = current.context { Text(context).font(.footnote) }
                }
            } else {
                ContentUnavailableView("沒有待複習的單字", systemImage: "checkmark.seal")
            }

            HStack(spacing: 24) {
                Button(action: { Task { await viewModel.submit(result: false) } }) {
                    Label("忘記", systemImage: "xmark.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.red)

                Button(action: { Task { await viewModel.submit(result: true) } }) {
                    Label("記得", systemImage: "checkmark.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
            }
            .padding(.horizontal)
        }
        .task { await viewModel.load() }
    }
}

struct SettingsView: View {
    @ObservedObject var viewModel: SettingsViewModel

    var body: some View {
        Form {
            Section(header: Text("Google 帳戶")) {
                Toggle("已登入", isOn: Binding(
                    get: { viewModel.settings.isSignedIn },
                    set: { $0 ? viewModel.signIn() : viewModel.signOut() }
                ))
            }

            Section(header: Text("同步頻率")) {
                Stepper(value: Binding(
                    get: { viewModel.settings.syncFrequencyMinutes },
                    set: { viewModel.updateFrequency($0) }
                ), in: 15...240, step: 15) {
                    Text("每 \(viewModel.settings.syncFrequencyMinutes) 分鐘自動同步")
                }
            }

            Section(header: Text("手動同步")) {
                Button(action: { Task { await viewModel.triggerSync() } }) {
                    Label("立即同步", systemImage: "icloud.and.arrow.down")
                }
                if let lastSynced = viewModel.settings.syncStatus.lastSyncedAt {
                    Text("上次同步：\(lastSynced.formatted(date: .abbreviated, time: .shortened))")
                        .font(.footnote)
                }
                if let error = viewModel.settings.syncStatus.lastError {
                    Text("錯誤：\(error)")
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }
        }
    }
}
