# Smart EA 報告自動化

這個資料夾接續 Claude 未完成的 Smart EA 環境稽核報告自動化任務。

目前完成範圍：

- 將業務回傳的 vendor Excel 轉成標準化 `Env. Data`、`Moisture`、`CFU` 工作表
- 使用人工標準化 Excel 作為參考，讀取 `Areas`、`ITEMLIST`、菌落計數 / `MISC.` 的 CFU count 與分離菌種
- 產出 PYS 測試案件的標準化 Excel，並另存一份保留正式範本公式的版本
- 產出 PYS 測試案件與人工版本的比對報告
- 產出環境面英文評語初稿與品質檢查紀錄
- 產出後台輸入用 JSON payload，讓自動輸入流程不用依賴人工檢查版 Excel

## 執行方式

使用 Codex bundled Python：

```bash
/Users/mac-4/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 smart_ea_automation.py
```

指定其他案件：

```bash
/Users/mac-4/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 smart_ea_automation.py \
  --vendor "/path/to/vendor.xlsx" \
  --target "/path/to/reference_standardized.xlsx" \
  --case-name "CASE_NAME"
```

## 網頁工具執行方式

第一版網頁工具已建立：

- `app.py`：Streamlit 網頁介面
- `run_web_tool.sh`：建立虛擬環境、安裝套件並啟動網頁
- `requirements.txt`：網頁工具需要的 Python 套件

啟動：

```bash
./run_web_tool.sh
```

預設網址：

```text
http://localhost:8501
```

若要給同事使用，工具主機可用：

```text
http://工具主機內網 IP:8501
```

目前網頁版已啟用：

- 自動偵測案件資料夾內的業務回傳環境資料 Excel
- 自動偵測人工標準化 / 公式範本 Excel
- 產出標準化 Excel
- 產出公式保留版 Excel
- 產出環境評論 Markdown / Excel / Word
- 產出評論依據 Markdown
- 產出後台輸入 JSON payload
- 產出 YIMS 填表計畫 JSON / Markdown
- 從網頁直接執行 YIMS API 檢查，不開瀏覽器
- 勾選確認後，從網頁透過 YIMS API 快速儲存
- 顯示資料列數與 quality issues

YIMS API 快速寫入腳本：

```bash
python yims_api_client.py \
  --payload "/path/to/CASE_backend_input_payload.json" \
  --order-id "669"
```

預設只檢查登入、案件、資料包與送出格式，不會儲存。確認要寫入 YIMS 時才加：

```bash
python yims_api_client.py \
  --payload "/path/to/CASE_backend_input_payload.json" \
  --order-id "669" \
  --save
```

YIMS 瀏覽器預覽腳本仍保留為 fallback：

```bash
python yims_bot.py \
  --payload "/path/to/CASE_backend_input_payload.json" \
  --metrics "/path/to/CASE_environment_metrics.json" \
  --order-id "663" \
  --keep-open
```

安全預設：

- `yims_api_client.py` 直接呼叫 YIMS 內部 endpoint `/api/orders/test_result/save/{order_id}`，速度比瀏覽器自動化快且穩。
- 預設不會儲存，只會產生 `yims_{order_id}_api_payload_preview.json`。
- 確認要儲存到 YIMS 時，才額外加 `--save`。
- 網頁工具可在側邊欄輸入 YIMS 帳號與密碼登入；帳密只傳給當次自動填表程式，不寫入輸出檔。
- 登入成功後會保存工具主機的瀏覽器登入狀態到 `.yims_auth_state.json`。
- 若不想在網頁輸入帳密，也可以先用終端機跑一次 `yims_bot.py` 手動登入。
- 目前腳本依據 2026-05-06 的 Playwright 操作快照與 YIMS 前端 bundle 還原。正式案件使用前，仍需先用測試案件複核畫面欄位與數值。

## PYS 測試輸出

輸出位置：`outputs/`

- `PYS_standardized_from_vendor.xlsx`：由腳本轉出的標準化 Excel
- `PYS_template_filled_with_formulas.xlsx`：複製正式 PYS Excel 範本後填入資料，保留原本公式欄位
- `PYS_conversion_validation.md`：與人工 PYS 標準化 Excel 的比對報告
- `PYS_environment_comments.md`：環境面英文評語初稿
- `PYS_comments_all.xlsx`：環境面評論 Excel
- `PYS_comments_all.docx`：環境面評論 Word
- `PYS_comment_basis.md`：評論生成依據與目前規則
- `PYS_environment_metrics.json`：評語使用的指標資料
- `PYS_backend_input_payload.json`：後台自動輸入使用的資料結構
- `PYS_yims_fill_plan.json`：YIMS 自動填表使用的 Vue state 結構
- `PYS_yims_fill_plan.md`：YIMS 填表預覽表
- `PYS_comment_quality_review.md`：與正式 PYS 報告評語的品質比對

## 公式版 Excel 填寫規則

- `Areas`：只填 `A:B` 的 Checking Point / Report Area，以及 `D:F` 的 Report Area / Function / RMW-PL-FGW-OUTSIDE；`G:H` 檢查欄保留公式。
- `Env. Data`：只填 `A` 的 Checking Point 與 `D:H` 的環境量測值；`B:C` 由公式依 `Areas` 帶出。
- `Moisture`：填 `A` 的 Checking Point、`D` 的 Classification、`E:J` 的物件與含水率；`B:C` 由公式依 `Areas` 帶出。
- `CFU`：填 `A:B` 的 Checking Point / Swab、`E:F` 的 Classification / Object；`C:D` 與 `G:H` 保留公式，由 `Areas`、`MISC.` / 菌落計數表帶出。

## 後台輸入用資料

後台自動輸入不直接讀人工檢查版 Excel，而是讀 `{case_name}_backend_input_payload.json`。這份資料已依後台操作方式整理：

- `indoor`：依主區域與評估區域分組，包含環境數據、含水率與微生物採樣。
- `outside`：室外參考數據，會寫入 YIMS「室外」欄位，並作為室內空間濕度滲透率與孢子空間滲透率的計算基準。
- `env`：每個評估區域底下，溫度、濕度、CO2、風速、PM10 都整理成陣列；輸入時要讓後台格數剛好等於陣列長度，避免空白格被平均成 0。
- `moisture`：每筆含 `category_to_select`、`object`、`values`，可直接對應後台下拉選單與輸入格。
- `microbiology`：後台「數值」欄輸入 `count_to_enter`；`isolate_mold_species_names` 由 `菌落計數表` 解析後轉成 YIMS 分離菌種。
- YIMS「分析參數選擇」由人先在後台設定；API 寫入時只保留後台既有值，不由腳本產生或改寫。
- `quality_issues`：列出缺少 area 或缺少 CFU count 等會阻擋後台輸入的問題。

## 目前驗證結果

PYS 案件第一輪驗證：

- `Moisture`：55 筆，與人工版一致
- `CFU`：24 筆，與人工版一致
- `Env. Data`：室內 21 筆與人工版一致，只有 4 筆風速差異
- 風速差異原因：原始 vendor 值為 `0.05 / 0.08 / 0.06`，人工版四捨五入為 `0.1`
- 腳本額外補入 Outside `O1` 到 `O5`，因為人工版目前缺這 5 筆
- 公式保留版已確認 `Env. Data`、`Moisture`、`CFU`、`Areas`、`KEY系統`、`菌落計數表` 仍含公式；`Moisture` 與 `CFU` 的 Classification 依實際流程由腳本填入。

## 已知限制

- 公式保留版是用 openpyxl 讀寫正式 Excel 範本；公式會保留，但 Excel 特定的資料驗證擴充可能不會被保留。
- `Humidity Permeability`、`Spore Infiltration`、`Air pollution level` 公式已由 Rose 確認：
  - Humidity Permeability = indoor average RH / outdoor average RH * 100
  - Spore Infiltration = indoor average PM10 / outdoor average PM10 * 100
- Air pollution level = PM10 average * 210
- `Environmental Mold Risk`、`Microbiological Risk`、`Overall Mold Risk` 會從 YIMS `/api/orders/print/data` 抓取正式後台計算結果，不由腳本自行重算。
- 評論生成資料索引放在 `references/smart_ea_parameter_definitions.md` 與 `references/PYS_case_comment_reference.md`。
- Classification 會優先沿用人工標準化 Excel 既有分類；新物件則用規則判斷，未來應整理成獨立對照表。

## 下一步

1. 確認 PYS 的環境面評語語氣是否可接受。
2. 補上微生物面評語生成。
3. 補上完整總評。
4. 用測試案件實際複核一次 YIMS 預覽填入畫面，再決定是否開放同事使用「填入並儲存」。
