# test_check_stock_clean.py 測試覆蓋項目

此測試檔案主要驗證 `check_stock_clean.py` 的核心功能與各種邏輯分支，確保系統在正常與異常情境下都能正確運作。

---

# 1. 規則解析與驗證 (Rule Parsing)

測試函式：`parse_rule`

測試內容：

- 正確解析規則資料
- 過濾無效規則資料

目的：

確保 API 或設定檔中的規則能被正確解析，並避免無效資料造成錯誤。

---

# 2. 規則取得 (Fetch Rules)

測試函式：`fetch_rules`

測試情境：

- 正常從 API 取得規則
- API 發生錯誤時回退到 **預設規則**
- API 回傳無效規則時回退到 **預設規則**

目的：

確保系統在 API 不穩定或資料異常時仍能正常運作。

---

# 3. LINE 訊息發送 (Send LINE Message)

測試函式：`send_line`

測試情境：

- 缺少 LINE Token 時 **不發送訊息**
- 正確發送 LINE payload
- LINE API 發送失敗時印出錯誤訊息

目的：

確保通知機制在不同狀態下能正確處理。

---

# 4. 市場開盤判斷 (Market Status)

測試函式：`is_market_open`

測試情境：

- 非交易時段
- 台股交易時段內
- 美股交易時段內
- 交易結束
- 台股交易時段起始邊界
- 美股交易時段結束邊界

目的：

確保系統只依照 **市場有效交易時段** 判斷是否執行。

---

# 5. 今日日線資料判斷 (Has Today Data)

測試函式：`has_today_data`

測試情境：

- close_series 為空時回傳 False
- 最後一筆日線不是今天時回傳 False
- 最後一筆日線是今天時回傳 True
- 台股 naive timestamp index（無時區）可正確判斷

目的：

確保系統只在資料完整且日期正確時才繼續產生報表，並能兼容台股常見資料型態。

---

# 6. 收盤價下載 (Download Close Prices)

測試函式：`download_close_prices`

測試內容：

- 美股：透過 `yf.Ticker(symbol).history(...)` 取得日線資料
- 台股：透過 `get_tw_close_prices` + `format_tw_close_series` 取得日線資料

目的：

確保美股/台股兩條下載流程都能正常運作。

---

# 7. 市場與報表時間輔助函式

測試函式：`get_market_timezone`、`is_today_final_report_time`

測試內容：

- `.TW` 代號映射到台北時區與台股市場
- 非 `.TW` 代號映射到紐約時區與美股市場
- 台股最終報表時間僅在 `14:05` 為 True
- 美股最終報表時間僅在 `16:45` 為 True

目的：

確保市場辨識與最終報表時間判斷符合預期。

---

# 8. 股票通知 Bubble 生成 (Stock Bubble)

測試函式：`build_stock_bubble`

測試情境：

- 市場未開時 **不生成**
- 今日資料不存在時 **不生成**
- 資料不足時 **不生成**
- 未達跌幅門檻且非最終報表時間 **不生成**
- 跌幅達門檻時 **生成**
- 最終報表時間時 **生成**
- 台股最終報表時間（14:05）即使未達跌幅門檻仍 **生成**
- 台股時區判斷
- 台股整合流程（market open + has_today_data + threshold）

目的：

確保 LINE Flex Message 只在 **跌幅達門檻** 或 **收盤後最終報表時間** 且已有當日日線資料時才生成。

---

# 9. 歷史資料格式化 (History Formatting)

測試函式：`format_history`

測試內容：

- 將歷史收盤價資料格式化為文字

目的：

確保顯示在 LINE 訊息中的歷史資料格式正確。

---

# 10. 主流程 (Main Flow)

測試函式：`main`

測試情境：

- 有股票通知 bubble 時發送 **carousel**
- 有發送時會呼叫 `logout_api`
- 沒有 bubble 時 **不發送訊息**
- 沒有發送時不呼叫 `logout_api`
- **即使 send_line 發生例外，logout_api 也一定會被呼叫**（try/finally 機制，有測試驗證）

目的：

確保整個系統流程能正常運作，並且在發送訊息失敗時也能安全登出資源。

---

# 11. shioaji_utils.py 工具模組單元測試

測試檔案：test_shioaji_utils.py

測試內容：

- `init_api`/`logout_api`：API 初始化與登出流程、快取與重複呼叫、資源釋放
- `get_tw_close_prices`：台股收盤價資料取得流程（含 symbol 處理、資料轉換）
- `get_recent_closing_prices`：資料分組、天數裁切、欄位正確性
- `format_tw_close_series`：DataFrame 轉 Series，index 與資料正確性

目的：

- 確保 shioaji_utils.py 工具模組的每個 function 都能獨立正確運作，並能被主流程安全調用。
- 測試 mock API 行為，避免連線外部資源。

---

# 測試覆蓋總結

目前測試已涵蓋：

- 規則解析與驗證
- API 取得規則與異常處理
- LINE 訊息發送
- 市場開盤判斷
- 市場/時區映射與最終報表時間判斷
- 當日日線資料判斷
- 股票資料下載
- Flex Message 生成
- 歷史資料格式化
- 系統主流程

這些測試涵蓋：

- **主要功能**
- **邏輯分支**
- **錯誤處理**
- **邊界情況**

只要測試全部通過，就可以放心修改 `check_stock_clean.py`，並確保核心功能不會被破壞。