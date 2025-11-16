# 資料契約與同步設計

本文件彙整目前 Flask/CLI 共用的 JSON 結構、Google Drive 同步需求與權杖管理流程，避免實作時產生行為落差。

## JSON 資料契約

- **檔案結構**：整個 `vocab.json` 為「物件陣列」，每一筆單字都是獨立物件。
- **共通欄位**（Flask 與 `scripts/vocab_tool.py` 都會讀寫，下列欄位缺漏時會被自動補齊）：
  | 欄位 | 型別 | 必填 | 說明 |
  | --- | --- | --- | --- |
  | `id` | string (UUIDv4) | 是 | 唯一識別單字。 |
  | `word` | string | 是 | 原始單字或片語。 |
  | `definition` | string | 是 | 釋義／翻譯內容。 |
  | `context` | string | 否（預設空字串） | 例句或筆記。 |
  | `created_at` | string (格式 `YYYY-MM-DD`) | 是 | 新增日期（UTC）。 |
  | `next_review` | string (格式 `YYYY-MM-DD`) | 是 | 下次複習日期（UTC）。若缺值會以 `created_at` 補上。 |
  | `interval_days` | integer | 是（預設 `1`） | 間隔天數（1–30），複習後根據記憶結果倍增或重置。 |
  | `success_streak` | integer | 是（預設 `0`） | 連續記對次數。 |
  | `review_count` | integer | 是（預設 `0`） | 累積複習次數。 |

- **延伸欄位**：未被上述清單列出的欄位（例如未來加入的標籤或例句來源）應視為選填，程式需容忍但不會主動修改。
- **日期格式**：所有日期皆為 `YYYY-MM-DD` 的 UTC 日期字串。若無法解析則當日視為已到期，避免遺漏複習。

## VOCAB_STORAGE 機制評估

- 現狀：`VOCAB_STORAGE` 僅用來指定單一 JSON 檔路徑（例如放在同步資料夾內）。對於 Google Drive 桌面版同步而言可行，但若要使用 Drive API，還缺少：
  - 本機快取目錄（避免直接在雲端檔案上覆寫）。
  - 上傳／下載流程與衝突解決規則。
  - 權杖與同步狀態檔案的位置。
- 結論：需要增設「本機快取 + API 同步」機制，`VOCAB_STORAGE` 仍可沿用為快取檔路徑，但同步腳本需額外讀寫自己的設定檔。

## 建議的本機快取 + Drive 同步流程

- **目錄與檔案**
  - 本機快取：`~/.enlearn/vocab.json`（或 `VOCAB_STORAGE` 指定的自訂路徑）。
  - 同步中繼檔：`~/.enlearn/sync_state.json`（保存 Drive 檔案 ID、最後同步時間、最後已知 revision ID）。
  - 日誌：`~/.enlearn/sync_log.json`（詳見後述）。

- **下載（Pull）流程**
  1. 讀取 `sync_state.json`，若尚未有 Drive 檔案 ID，先呼叫 Drive API 以檔名搜尋或建立檔案並儲存 ID。
  2. 取得雲端檔案的 `modifiedTime` 與 `headRevisionId`。若雲端版本較新或本機不存在，下載內容至暫存檔，驗證為合法 JSON 陣列後覆蓋本機快取。
  3. 更新 `sync_state.json` 的最後同步時間與 `headRevisionId`。

- **上傳（Push）流程**
  1. 驗證本機快取格式，並從 `sync_state.json` 取出上一個 `headRevisionId`。
  2. 透過 Drive API 的 `If-Match`/`ifGenerationMatch`（或 `If-None-Match`）機制附帶 revision 以避免覆寫較新的雲端版本。
  3. 上傳成功後記錄新的 `modifiedTime` 與 `headRevisionId` 至 `sync_state.json`。

- **同步觸發點**
  - 手動指令：新增 `scripts/sync_vocab.py`（未來實作）提供 `pull` / `push` / `sync` 三種子命令。
  - 自動：可在 Flask 啟動或 CLI 執行前後掛勾同步，但需尊重使用者無網路或純離線使用的需求，應提供「僅本機」模式。

## Google Drive 授權與權杖儲存

- **建議 API**：採用 Google Drive REST API（使用官方 Python client），適合桌面/CLI/Web 混合場景。iOS SDK 僅適用於原生 App，不符合現有技術棧。
- **OAuth 授權類型**：Installed App（`urn:ietf:wg:oauth:2.0:oob` 或 localhost redirect）。授權範圍建議限定為 `https://www.googleapis.com/auth/drive.file` 以便只操作使用者自行建立的檔案。
- **權杖存放與更新**
  - `~/.enlearn/drive_token.json`：保存 access token、refresh token、取得時間與過期時間。
  - 初次授權後將 refresh token 寫入並設定檔案權限為 600。
  - 每次同步前檢查有效期限，必要時透過 refresh token 換取新的 access token，成功後回寫檔案。
  - 若 refresh token 遺失或失效（收到 401/invalid_grant），提示使用者重新執行授權流程並覆寫 `drive_token.json`。

## 衝突解決與版本策略

- **版本依據**
  - 雲端：使用 Drive 的 `modifiedTime`（UTC）與 `headRevisionId`。
  - 本機：使用檔案 `mtime` 和 `sync_state.json` 中紀錄的最後同步 revision。

- **處理規則**
  - **單向較新覆蓋**：若本機 `mtime` 晚於最後同步時間且雲端 `modifiedTime` 未變，允許直接上傳覆寫。
  - **雲端較新**：若雲端 `modifiedTime` 晚於最後同步時間，先下載，再將本機變更與雲端版本進行合併（以 `id` 為主鍵），最後上傳新的合併結果。
  - **雙方都有新變更**：以 `id` 為粒度合併。當同一 `id` 的欄位同時被修改，採較新的 `next_review`/`review_count` 與 `success_streak`，並保留較長的 `context` 以減少資訊遺失，必要時將衝突的兩個版本都寫入日誌。
  - **無法判定**：保留雲端檔案為主，並將本機版本存成 `vocab.local-backup-<timestamp>.json`，於日誌中提示需要人工處理。

## 同步狀態與錯誤記錄

- **`sync_log.json` 格式（附加寫入）**
  ```jsonc
  [
    {
      "ts": "2024-05-16T12:34:56Z",
      "direction": "pull" | "push" | "sync",
      "status": "success" | "skipped" | "failed",
      "local_mtime": "2024-05-16T12:00:00Z",
      "drive_modified": "2024-05-16T12:10:00Z",
      "revision": "<headRevisionId>",
      "details": "text message or error stack trace"
    }
  ]
  ```
  - 只需追加寫入，不覆蓋舊紀錄。
  - 如遇異常（HTTP 409/412 等），將錯誤碼與訊息寫入 `details`。

- **日誌輪替**：檔案大於 5 MB 時將舊檔案改名為 `sync_log-<timestamp>.json`，重新建立空白陣列。

- **使用者提示**：Flask/CLI 可在同步失敗時於介面或終端機顯示「同步失敗，請檢查 sync_log.json」，並繼續允許本機離線存取，避免阻斷核心功能。
