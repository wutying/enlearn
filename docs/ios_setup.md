# iOS 開發環境需求與初始化指引

本文件協助你準備 iOS 版 Enlearn Vocabulary Helper 的基礎設定，包括必要的 Apple 開發者資格、Bundle ID、Google OAuth Client ID 與 Xcode 專案初始化步驟。

## 先決條件

- macOS（建議最新版）與 Xcode 15 以上。
- Apple Developer 帳號（個人或組織），可建立 Bundle ID 與簽署測試版。
- 可登入 Google Cloud Console 並建立 OAuth 用戶端。

## Bundle ID 與簽章設定

1. 決定唯一的 Bundle ID，例如 `com.example.enlearn`，並在 Apple Developer 帳號中建立 App ID。
2. 在 Xcode 的「Signing & Capabilities」啟用自動管理簽章，選擇你的 Team。
3. 若需 Push/Background Modes，可在同一頁加上「Background Modes」並勾選需要的項目（例如 Background Fetch 以便後台同步）。

## 建立 Google OAuth Client ID（iOS）

1. 前往 [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 建立 OAuth 2.0 用戶端。
2. 類型選擇 **iOS**，Bundle ID 填入上述的 `com.example.enlearn`。
3. 下載憑證（`GoogleService-Info.plist` 或顯示的 Client ID 字串）。
4. 在 Xcode 專案中：
   - 將 `GoogleService-Info.plist` 加入專案並確保包含在所有目標（Targets）。
   - 於 `Info` → `URL Types` 加入 Reversed Client ID（`com.googleusercontent.apps.<client-id>`），供 Google Sign-In 回跳使用。

## Xcode 專案初始化步驟（範例）

1. 在 Xcode 建立 **App** 專案，介面 SwiftUI、語言 Swift，填入前述 Bundle ID。
2. 新增 Swift Package 或 CocoaPods 依賴（若需要 Google Sign-In/Drive SDK，可加入 `GoogleSignIn`、`GoogleAPIClientForREST/Drive`）。
3. 在 `Info.plist` 中加入：
   - `NSPhotoLibraryAddUsageDescription`（若需匯出圖片）或其他相關權限。
   - `CFBundleURLTypes` 中的 URL Scheme（Reversed Client ID）。
4. 建立網路層設定：
   - 若 iOS 需要呼叫桌面端 API，將桌面 IP 加入 `ATS` 例外（`NSAppTransportSecurity` → `NSExceptionDomains`）。
   - 或者直接操作 Google Drive 檔案：預設讀寫 `vocab.json`，與桌面版 `VOCAB_STORAGE` 保持一致。
5. 驗證：
   - 執行一次模擬器或實機，確保能成功透過 Google 帳號登入並讀寫 Drive 上的 `vocab.json`。
   - 若透過 API，確認可成功從 `http://<桌面IP>:5000` 取得單字列表並新增資料。

## 推薦專案結構（簡述）

```
Enlearn-iOS/
├─ Enlearn/            # App 主程式碼與 UI
├─ EnlearnTests/       # 單元測試
├─ EnlearnUITests/     # UI 測試
├─ Config/             # .xcconfig、環境常數（如 API Base URL、Drive 檔案路徑）
└─ Resources/          # GoogleService-Info.plist、App Icons
```

## 同步與除錯提示

- 建議在 `Config` 中加入 `VOCAB_STORAGE_PATH` 或 `API_BASE_URL`，以便不同環境（模擬器、實機、預設值）切換。
- 若遇到 Drive 權限錯誤，確認 OAuth 同意畫面已發佈並包含 `.../auth/drive.file` 權限。
- 若需要重新整理登入狀態，清除 Keychain 或在 Google 帳號設定中移除舊的應用存取權限後再重新登入。

