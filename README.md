# Enlearn Vocabulary Helper

This project gives you a **隨身單字本** that works both as a friendly web app and as a quick command-line companion. All vocabulary is saved in a single JSON file so you can sync it across devices with Dropbox, iCloud, or any other tool you prefer.

## 功能重點

- **立即新增**：在新增單字時會自動查詢翻譯（需網路連線），直接帶入欄位讓你確認或微調，再加上例句就能一起存好。系統透過 Google 翻譯的公開端點提供查詢，一次帶出同一個單字的多種可能意思，讓你保留完整語意。
- **雙重複習模式**：可在複習頁面切換「顯示單字猜解釋」或「顯示解釋輸入單字」，依照當天狀態自由選擇。
- **進度追蹤**：系統會統計每個單字的複習次數與連勝紀錄，幫助你掌握學習成效。
- **跨裝置同步**：資料儲存在 `~/.enlearn/vocab.json`，只要同步這個檔案就能在多個裝置上持續累積。
- **保留 CLI 工作流程**：偏好終端機的使用者仍可使用原本的 `scripts/vocab_tool.py` 指令快速操作。

## 從零開始：一步一步架設網頁 APP

以下步驟假設你剛從 GitHub 下載專案，不論是 `git clone` 或下載 ZIP 後解壓縮都適用。

1. **挑選資料夾**：建議在個人專案資料夾內建立一個新目錄，例如：

   ```bash
   mkdir -p ~/Projects
   cd ~/Projects
   ```

2. **取得程式碼**：

   - 使用 Git：

     ```bash
     git clone https://github.com/<你的帳號>/enlearn.git
     cd enlearn
     ```

   - 或者在 GitHub 介面點選 **Download ZIP**，解壓縮後把整個 `enlearn` 資料夾搬到上述的 `~/Projects` 內，再用檔案總管或終端機進入該資料夾。

   > 只要「`app/`、`scripts/`、`vocab/`」這些資料夾仍在同一層，即可照著下列步驟執行，無需放在特定系統路徑。

3. **確認 Python 與 pip**：

   - macOS/Linux：在終端機輸入 `python3 --version`。若顯示 3.9 以上版本即可使用。
   - Windows：可從 [python.org](https://www.python.org/downloads/) 安裝最新版 Python，安裝時勾選「Add python.exe to PATH」。

4. **建立虛擬環境與安裝套件**（建議做法，避免影響系統其他專案）：

   - macOS/Linux：

     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     pip install -r requirements.txt  # 若沒有此檔，可改用下一行安裝 Flask
     pip install flask
     ```

   - Windows（PowerShell）：

     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     python -m pip install --upgrade pip
     pip install flask
     ```

   > 若日後重新開啟終端機，記得再次執行 `source .venv/bin/activate`（或 Windows 版本的 Activate 指令）讓虛擬環境生效。

5. **設定資料儲存路徑（選擇性）**：預設單字會儲存在 `~/.enlearn/vocab.json`。若想將 JSON 檔放到 Dropbox、Google Drive 等資料夾，啟動前可設定環境變數：

   - macOS/Linux：

     ```bash
     export VOCAB_STORAGE=~/Dropbox/vocab.json
     ```

   - Windows（PowerShell）：

     ```powershell
     setx VOCAB_STORAGE "C:\\Users\\你的帳號\\Dropbox\\vocab.json"
     $env:VOCAB_STORAGE="C:\\Users\\你的帳號\\Dropbox\\vocab.json"  # 立即生效
     ```

   > 翻譯查詢預設會將英文轉成繁體中文（`EN|ZH-TW`），並透過 `https://translate.googleapis.com/translate_a/single` 的公開 Google 翻譯端點取得所有可用的翻譯與字典釋義。若你習慣不同語言組合，可於啟動前設定 `TRANSLATION_LANGPAIR` 環境變數，例如：

   - macOS/Linux：

     ```bash
     export TRANSLATION_LANGPAIR=EN|JA
     ```

   - Windows（PowerShell）：

     ```powershell
     setx TRANSLATION_LANGPAIR "EN|JA"
     $env:TRANSLATION_LANGPAIR="EN|JA"  # 立即生效
     ```

   > 語言代碼需為 2～3 個英文字母，可選擇性加上連字號與地區（如 `EN`、`EN-US`、`ZH-TW`、`SR-LATN`）。如果輸入的語言代碼不符合 API 的格式（例如出現 `AUTO`），系統會自動改用預設的 `EN|ZH-TW`，確保翻譯查詢仍能成功。

6. **啟動伺服器**：

   ```bash
   flask --app app.app --debug run
   ```

   如果你使用的是 Windows PowerShell，指令一樣，只是確保前一步已成功啟用虛擬環境。

   - **想要從外部網路連線？** 將監聽位址改成所有網卡，並明確指定埠號：

     ```bash
     flask --app app.app --debug run --host 0.0.0.0 --port 5000
     ```

     這會讓 Flask 在所有可用的網路介面上提供 5000 埠服務，方便你搭配路由器的 Port Forwarding 或 VPN 讓其他裝置連入。請同時確保作業系統防火牆與網路設備已開放 5000 埠，並留意外部公開服務的安全性。

7. **開啟瀏覽器**：造訪 <http://127.0.0.1:5000> 或 <http://localhost:5000>。

   - 左側卡片輸入單字時會即時查詢翻譯，確認後即可儲存。
   - 下方列表可查看所有單字、下一次複習時間與累積複習次數。
   - 右上角「開始複習」能切換兩種複習模式，系統會記錄結果並安排下次提醒。

8. **（選擇性）新增手機捷徑**：在手機瀏覽器開啟同一網址後加入主畫面，方便像 APP 一樣啟用。

> 若要停止伺服器，在終端機按下 `Ctrl + C` 即可；下次使用時從步驟 4 重新啟用虛擬環境、再執行步驟 6。

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

## 常見問題排查

### 瀏覽器開不到 <http://127.0.0.1:5000>

1. **確認伺服器有成功啟動**：切換回執行 `flask --app app.app --debug run` 的終端機視窗，畫面上應該看到 `* Running on http://127.0.0.1:5000`。若程式立即結束或顯示錯誤訊息，先依照錯誤內容處理（常見如缺少套件、語法錯誤）。
2. **重新執行啟動指令**：確保目前的工作目錄是在專案根目錄（能看到 `app/` 與 `scripts/`），再輸入：

   ```bash
   flask --app app.app --debug run
   ```

   若你是在虛擬環境中執行，記得先 `source .venv/bin/activate`（或 Windows 的 `./.venv/Scripts/Activate.ps1`）。
3. **檢查 5000 埠是否被占用**：

   - macOS/Linux：

     ```bash
     lsof -i:5000
     ```

     如果看到其他程式占用 5000 埠，先關閉該程式或改用 `flask --app app.app run --port 5001` 啟動。
   - Windows（PowerShell）：

     ```powershell
     netstat -ano | findstr 5000
     ```

     找出 PID 後，可在「工作管理員」或使用 `taskkill /PID <PID> /F` 結束該程序。
4. **防火牆或安全性軟體**：部分企業或學校電腦會封鎖本機連線。嘗試改用 `http://localhost:5000`，或暫時關閉／允許本機伺服器的連線。
5. **確認瀏覽器網址輸入正確**：開啟新分頁直接貼上 `http://127.0.0.1:5000`（或 `http://localhost:5000`），不要遺漏 `http://`。
6. **查看 Flask 日誌**：伺服器終端機會即時顯示請求紀錄與錯誤。如果瀏覽器還是沒有回應，留意是否有例外（Exception）或 Traceback 訊息，根據內容修正後再重新啟動。

如上述步驟仍無法解決，可以將終端機顯示的完整錯誤訊息提供出來，便於進一步協助。
