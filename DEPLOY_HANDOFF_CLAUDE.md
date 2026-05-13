# Smart EA Streamlit Deployment Handoff for Claude Code

建立日期：2026-05-13  
窗口：Codex  
接手方：Claude Code  
目標：把 Smart EA 網頁工具整理成可安全推上 GitHub、並用 Streamlit Community Cloud 發布給同事使用的版本。

## 目前工具位置

工作目錄：

```text
/Users/mac-4/Desktop/rose-agent/100_Todo/projects/smart-ea-automation
```

主要入口：

- `app.py`：Streamlit 網頁工具
- `smart_ea_automation.py`：Excel 整理與輸出核心流程
- `yims_api_client.py`：YIMS API 檢查 / 儲存
- `yims_payload_builder.py`：YIMS payload 組裝
- `rule_based_comment_generator.py`：不用 API 的固定邏輯評論生成器
- `references/smart_ea_parameter_definitions.md`：評論生成規則與參數定義
- `references/PYS_case_comment_reference.md`：PYS 正式報告案例參考
- `requirements.txt`：目前本機依賴
- `.gitignore`：Codex 已先加防呆，避免推送帳密與客戶資料
- `.streamlit/secrets.toml.example`：Streamlit Cloud secrets 範例

## 最新已驗收狀態

已完成且本機可用：

- 上傳 / 偵測 Excel
- 產生整理後 Excel
- 產生公式保留版 Excel
- 產生 YIMS 後台輸入 payload
- YIMS API 快速檢查 / 儲存流程
- 從 YIMS API 抓回環境面風險、微生物面風險、整體風險
- 產生不用 OpenAI API 的英文評論文字檔

最新評論輸出檔：

```text
/Users/mac-4/Desktop/S.EA test/整理輸出/SEA_test_rule_based_comments.txt
```

目前評論規則已修正：

- 正式報告語氣：過去式，使用 `could / may / might / potential`
- 不寫建議，只寫影響
- 不提 `Temperature`
- 物件名稱自然小寫，例如 `carton boxes`、`wooden racks`
- 不使用 `Carton Box (outer packaging)` 這種括號格式
- 小評論會寫實際超標物件及物件影響
- `Overall Environmental Comment` 與 `Overall Microbiology Comment` 改成跨倉間綜合評論，不重複列小評論明細

## Streamlit Cloud 官方部署依據

請以官方文件為準：

- File organization：`https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization`
- App dependencies：`https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies`
- Secrets management：`https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management`
- Deploy app：`https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy`

重點：

- Community Cloud 會從 GitHub repo 執行 app。
- `requirements.txt` 要在 repo root 或 app entrypoint 同目錄。
- 帳密與 API key 不可放 GitHub，要放 Streamlit Cloud Advanced settings 的 Secrets。
- Streamlit 官方明確提醒：`.streamlit/secrets.toml` 不可 commit。

## GitHub 發布前必做安全檢查

絕對不要 commit：

- `.env`
- `.streamlit/secrets.toml`
- `.yims_auth_state.json`
- `.venv/`
- `outputs/`
- `uploads/`
- `web_outputs/`
- `99_logs/`
- 客戶 Excel、產出 Excel、Word、PDF

已新增 `.gitignore`，但 Claude 接手前仍要再跑一次掃描。

建議檢查指令：

```bash
cd /Users/mac-4/Desktop/rose-agent/100_Todo/projects/smart-ea-automation
find . -maxdepth 3 -type f | sort
rg -n "OPENAI_API_KEY|YIMS_ACCOUNT|YIMS_PASSWORD|Bearer|XSRF|password|api_key|secret|token" . --hidden -g '!.venv/**' -g '!outputs/**' -g '!uploads/**' -g '!web_outputs/**' -g '!99_logs/**'
```

如果掃到真實密鑰或帳密，先移除再 git init / commit。

## 建議 GitHub repo 結構

不要把整個 `rose-agent` 推上 GitHub。請只建立 Smart EA 工具專用 repo，或複製乾淨版本到新資料夾。

建議 repo root：

```text
smart-ea-automation/
├── app.py
├── smart_ea_automation.py
├── yims_api_client.py
├── yims_payload_builder.py
├── rule_based_comment_generator.py
├── comment_generator.py
├── _legacy_comments.py
├── requirements.txt
├── README.md
├── DEPLOY_HANDOFF_CLAUDE.md
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
└── references/
    ├── smart_ea_parameter_definitions.md
    └── PYS_case_comment_reference.md
```

是否保留：

- `yims_bot.py`：若 Streamlit Cloud 不支援 Playwright browser fallback，就先不要讓 UI 顯示瀏覽器 fallback。
- `comment_generator.py`：目前 ChatGPT API 生成仍不是主線，可保留但 UI 建議標成進階/測試。
- `outputs/`：不要 commit。

## Claude 需要優先處理的部署改造

### 1. 移除雲端不適用的本機預設路徑

目前 `app.py` 有本機預設：

```python
DEFAULT_CASE_DIR = Path("/Users/mac-4/Desktop/S.EA test")
```

在 Streamlit Cloud 上無效。建議：

- Cloud 模式預設只提供「上傳 Excel」
- 「主機資料夾」只在本機開發模式顯示
- 不要在雲端 UI 顯示 Rose 本機路徑

### 2. Secrets 讀取方式

目前主要讀 `os.getenv()`。Streamlit secrets root-level key 也可變成環境變數，但建議 Claude 補 helper：

```python
def get_secret(name: str, default: str = "") -> str:
    if name in st.secrets:
        return str(st.secrets[name])
    return os.getenv(name, default)
```

要支援：

- `OPENAI_API_KEY`
- `YIMS_ACCOUNT`
- `YIMS_PASSWORD`

不要把帳密寫入檔案。

### 3. YIMS 登入狀態

目前本機會使用 `.yims_auth_state.json` 保存登入狀態。雲端部署不能依賴這個檔案，也不能 commit。

建議雲端版：

- 以 `YIMS_ACCOUNT` / `YIMS_PASSWORD` secrets 每次建立 requests session。
- 若 YIMS / Cloudflare 阻擋 Streamlit Cloud IP，要回報 Rose：雲端只能做 Excel + 評論，YIMS 寫入需留在內網或本機工具。

### 4. Playwright 依賴

目前 `requirements.txt` 有 `playwright`，但主線已改 YIMS API，不應讓雲端版依賴瀏覽器自動化。

建議：

- 若不需要瀏覽器 fallback，從雲端 requirements 移除 `playwright`。
- 若要保留，要確認 Streamlit Cloud 是否能安裝瀏覽器與相關 system packages，可能需要額外設定，不建議作為第一版。

### 5. 依賴版本

目前 `requirements.txt` 未 pin 版本。Streamlit 官方建議 pin Streamlit 版本。Claude 需用本機測過的版本固定一版。

至少確認：

```bash
python -m pip freeze
```

再決定要 pin 到哪個版本。

### 6. 網頁權限與公司使用

Streamlit Community Cloud 的分享與權限要由 Rose / 公司帳號決定。部署時請優先用 private GitHub repo，並確認 Streamlit app viewer 權限。

不要把客戶資料或 YIMS 帳密放在公開 repo。

## 驗收標準

Claude 完成後請驗收：

- GitHub repo 只含乾淨工具檔案，沒有 `.env`、登入狀態、客戶 Excel、輸出報告。
- Streamlit Cloud 可成功啟動 app。
- 同事可透過瀏覽器開啟工具。
- 雲端版預設使用「上傳 Excel」流程，不顯示 Rose 本機路徑。
- 上傳測試 Excel 後可產生整理後 Excel、公式保留版 Excel、YIMS payload、評論文字檔。
- 評論文字檔仍符合最新規則：無括號物件格式、不提 Temperature、不寫建議、overall 為綜合評論。
- 若啟用 YIMS API：先跑不儲存檢查，成功後才允許儲存。
- 若 YIMS 在 Streamlit Cloud 被阻擋，需在 README 寫明限制與本機替代流程。

## 建議驗證指令

```bash
cd /Users/mac-4/Desktop/rose-agent/100_Todo/projects/smart-ea-automation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m py_compile app.py smart_ea_automation.py yims_api_client.py yims_payload_builder.py rule_based_comment_generator.py
python -m streamlit run app.py
```

安全掃描：

```bash
git status --short
git check-ignore -v .env .yims_auth_state.json .venv outputs uploads web_outputs 99_logs
rg -n "OPENAI_API_KEY|YIMS_ACCOUNT|YIMS_PASSWORD|Bearer|XSRF|password|api_key" . --hidden -g '!.venv/**' -g '!outputs/**' -g '!uploads/**' -g '!web_outputs/**' -g '!99_logs/**'
```

## 回報給 Rose 的格式

請 Claude 最後回報：

- GitHub repo URL
- Streamlit app URL
- 已處理的安全項目
- 可用功能
- YIMS API 在雲端是否可用
- 已知限制與同事使用方式
