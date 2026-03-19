# StockAlertJob 專案筆記（關鍵邏輯與關鍵數字）

## 1) 專案目的與輸出

此專案會依規則檢查股票在「短線 / 長線」區間的漲跌幅，符合條件時組出 LINE Flex Message 並廣播。

核心輸出：
- 有觸發條件：送出 carousel（可含多檔 bubble）
- 無觸發條件：不送訊息

主要入口：
- `check_stock.py` 的 `main()`

---

## 2) 執行流程（從 main 讀一次就懂）

1. `fetch_rules()`
- 從 `CONFIG_API_URL` 取設定。
- 載入規則清單 `rules`。
- 同步載入長線設定 `long_term_drop.days`、`long_term_drop.drop_percent`。
- 若 API 錯誤或規則無效：回退到預設規則。

2. 逐檔規則執行 `build_stock_bubble(rule)`
- 決定市場時區（`.TW` => 台股，其他 => 美股）。
- 非 `FORCE_SEND_REPORT` 時，先檢查是否在交易時段內。
- 下載日線 close（目前統一用 yfinance 路徑）。
- 非 `FORCE_SEND_REPORT` 時，確認最後一筆是否為當日資料。
- 檢查資料量是否足夠（至少 `max(x_days, LONG_TERM_LOOKBACK_DAYS)` 筆）。
- 計算短線 / 長線漲跌幅。
- 判斷觸發條件（短線達門檻、長線達門檻、最終報表時間、或強制送出）。
- 觸發才組 bubble，否則回傳 `None`。

3. 聚合 bubble
- 至少一個 bubble 才 `build_carousel()` + `send_line()`。
- `send_line()` 後一定 `logout_api()`（`try/finally`）。

---

## 3) 關鍵常數與數字（最常改、最容易影響行為）

定義位置：`check_stock.py`

- `DEFAULT_LOOKBACK_PADDING_DAYS = 5`
- `DEFAULT_LONG_TERM_LOOKBACK_DAYS = 60`
- `DEFAULT_LONG_TERM_DROP_PERCENT = 10.0`

執行期可被 API 覆蓋：
- `LONG_TERM_LOOKBACK_DAYS`（預設 60）
- `LONG_TERM_DROP_PERCENT`（預設 10.0）

規則預設值（當 API 失敗或 rules 無效）：
- `0050.TW, 5 天, 5%`
- `VOO, 5 天, 5%`
- `VT, 5 天, 5%`

日線下載天數：
- `required_days = max(x_days, LONG_TERM_LOOKBACK_DAYS) + 5`

---

## 4) 時間與市場規則（實務上最關鍵）

來源：`check_stock_utils.py`

市場辨識：
- 代號以 `.TW` 結尾 => 台股 / `Asia/Taipei`
- 否則 => 美股 / `America/New_York`

交易時段：
- 台股：08:00 ~ 15:00
- 美股：08:00 ~ 17:00

最終報表時間（即使未達跌幅門檻也可送）：
- 台股：14:05
- 美股：16:45

`FORCE_SEND_REPORT=true` 時：
- 可略過「交易時段」與「今日資料」限制
- 但仍需有足夠資料計算 lookback

---

## 5) 觸發邏輯（何時送）

短線觸發：
- `drop < 0` 且 `abs(drop) >= rule.y_percent`

長線觸發：
- `drop < 0` 且 `abs(drop) >= LONG_TERM_DROP_PERCENT`

最終送出條件（四選一）：
- `FORCE_SEND_REPORT`
- 短線觸發
- 長線觸發
- 最終報表時間

告警狀態字串（log 用）：
- `FORCED_SEND`
- `ALERT(short+long)`
- `ALERT(short)`
- `ALERT(long)`
- `FINAL_REPORT`

---

## 6) LINE Flex 內容重點

來源：`flex_msg_tpl.py`

bubble 會同時呈現：
- 短線區間：`short_lookback_days`、短線漲跌幅、短線 threshold 判斷
- 長線區間：`long_lookback_days`、長線漲跌幅、長線 threshold 判斷
- 各自獨立顏色規則，不互相覆蓋

顏色規則：
- 上漲：綠色
- 跌幅達門檻：紅色
- 其他：灰黑色

---

## 7) API 與環境變數

來源：`README`

主要變數：
- `CONFIG_API_URL`
- `LINE_TOKEN`
- `FORCE_SEND_REPORT`

永豐相關（給 `shioaji_utils.py` 用）：
- `SINOPAC_API_KEY`
- `SINOPAC_SECRET_KEY`
- `SINOPAC_CA_PATH`
- `SINOPAC_CA_PW`
- `SINOPAC_PERSON_ID`

Config API 建議欄位：
- `long_term_drop.days`
- `long_term_drop.drop_percent`
- `rules[]`（含 symbol / x_days / y_percent）

---

## 8) 測試覆蓋現況（對照 TEST_CASES）

目前整體覆蓋率（`coverage_summary.txt`）：
- TOTAL: 94%
- `check_stock.py`: 98%
- `check_stock_utils.py`: 91%
- `shioaji_utils.py`: 100%
- `flex_msg_tpl.py`: 21%

與 `test/TEST_CASES.md` 對照結論：
- `check_stock.py` 主流程與關鍵分支：已相當完整。
- `check_stock_utils.py` / `shioaji_utils.py`：已有明確單元測試。
- 主要不足：`flex_msg_tpl.py` 幾乎未覆蓋（21%），目前多數訊息格式僅間接驗證。

---

## 9) 目前可補強的測試點（優先順序）

P1（高）：
- `flex_msg_tpl.py`
  - `_resolve_drop_color` 的邊界值（等於 threshold）
  - `_build_trigger_text` 在 `None` 與極值時輸出
  - `build_bubble()` 欄位完整性（key 存在、文字格式、final report title suffix）
  - `build_carousel()` 空陣列/多 bubble 行為

P2（中）：
- `check_stock.py`
  - `send_line()` 的 requests 例外（目前測了 status >= 400，未測 request exception）
  - `_resolve_alert_status()` 各分支獨立單測（coverage 提示仍有漏分支）
  - `_get_close_point_days_ago()` 資料不足回傳 `(None, None)`

P3（中）：
- `check_stock_utils.py`
  - `_format_date_only()` 與 `print_close_series_with_index()` 的輸出格式測試
  - `_env_to_bool()` 大小寫與空白輸入組合

P4（低）：
- `download_close_prices()` 台股 shioaji 分支目前停用且測試 skip。
  - 若未來重啟，應取消 skip 並補 API 分頁/超過 14 天場景。

---

## 10) 維護時的快速檢查清單

每次改動後建議確認：
- 改動是否影響以下關鍵時點：台股 14:05、美股 16:45。
- 規則來源異常時，是否仍回退預設規則 + 長線預設值 60/10。
- 短線與長線門檻是否仍分離判斷。
- `FORCE_SEND_REPORT` 是否只放寬 gating，不破壞資料長度安全檢查。
- `main()` 是否維持「有送出才 logout，且 send_line 出錯仍 logout」。

---

## 11) 一句話總結

這個專案的關鍵在於：
「以市場時區和固定報表時點為主軸，結合短線/長線兩套跌幅門檻，確保在資料可用且規則可回退的前提下，穩定地輸出 LINE 股票報表。」
