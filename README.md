# Enlearn Vocabulary Helper

This project gives you a **隨身單字本** that works both as a friendly web app and as a quick command-line companion. All vocabulary is saved in a single JSON file so you can sync it across devices with Dropbox, iCloud, or any other tool you prefer.

## 功能重點

- **立即新增**：在新增單字時會自動查詢翻譯（需網路連線），直接帶入欄位讓你確認或微調，再加上例句就能一起存好。
- **雙重複習模式**：可在複習頁面切換「顯示單字猜解釋」或「顯示解釋輸入單字」，依照當天狀態自由選擇。
- **進度追蹤**：系統會統計每個單字的複習次數與連勝紀錄，幫助你掌握學習成效。
- **跨裝置同步**：資料儲存在 `~/.enlearn/vocab.json`，只要同步這個檔案就能在多個裝置上持續累積。
- **保留 CLI 工作流程**：偏好終端機的使用者仍可使用原本的 `scripts/vocab_tool.py` 指令快速操作。

## 快速開始：啟動網頁 APP

1. 建議使用虛擬環境並安裝依賴：

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install flask
   ```

2. 啟動伺服器：

   ```bash
   flask --app app.app --debug run
   ```

3. 在瀏覽器開啟 <http://127.0.0.1:5000>，即可使用：

   - 左側卡片輸入單字即自動查詢翻譯，可直接保存或調整後再送出。
   - 下方列表查看所有單字與下一次複習時間。
   - 右上角點「開始複習」進入複習模式，可在頁面上切換兩種複習方式，並按下對應按鈕或輸入答案讓系統安排下一次複習。

> **Tip:** 如果想把資料放到其他位置（例如雲端同步資料夾），可在啟動前設定環境變數：
>
> ```bash
> export VOCAB_STORAGE=~/Dropbox/vocab.json
> flask --app app.app run
> ```

## Command Line 使用方式（選擇性）

CLI 使用同一份資料庫，適合在終端機或自動化腳本中操作。

- 新增單字：

  ```bash
  python scripts/vocab_tool.py add WORD "Definition or translation" --context "Optional context"
  ```

- 複習單字：

  ```bash
  python scripts/vocab_tool.py review
  ```

  依照提示輸入 `y`（記得）、`n`（忘記）或 `q`（提早結束）。

- 查看列表：

  ```bash
  python scripts/vocab_tool.py list --limit 10
  ```

所有指令皆可加入 `--storage PATH` 指定自訂位置（與網頁 APP 的 `VOCAB_STORAGE` 相容）。

## 習慣養成建議

- 在手機主畫面加入捷徑，快速開啟網頁 APP。
- 每天安排 5 分鐘複習，讓系統自動幫你安排間隔。
- 閱讀時先用筆記 App 收集生字，回到電腦或手機時再一次輸入。
- 定期備份 `~/.enlearn/vocab.json`，避免資料遺失。

Happy learning!
