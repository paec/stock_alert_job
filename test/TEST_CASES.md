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
- 無即時資料
- 資料過舊
- 交易結束
- 資料時間新鮮
- 跨時區資料判斷

目的：

確保系統只在 **市場有效交易時段** 運作。

---

# 5. 收盤價下載 (Download Close Prices)

測試函式：`download_close_prices`

測試內容：

- 正確下載股票收盤價資料

目的：

確保 `yfinance` 資料取得流程正常。

---

# 6. 股票通知 Bubble 生成 (Stock Bubble)

測試函式：`build_stock_bubble`

測試情境：

- 市場未開時 **不生成**
- 資料不足時 **不生成**
- 未達跌幅門檻且非整點 **不生成**
- 跌幅達門檻時 **生成**
- 整點時 **生成**
- 台股時區判斷

目的：

確保 LINE Flex Message 的生成條件正確。

---

# 7. 歷史資料格式化 (History Formatting)

測試函式：`format_history`

測試內容：

- 將歷史收盤價資料格式化為文字

目的：

確保顯示在 LINE 訊息中的歷史資料格式正確。

---

# 8. 主流程 (Main Flow)

測試函式：`main`

測試情境：

- 有股票通知 bubble 時發送 **carousel**
- 沒有 bubble 時 **不發送訊息**

目的：

確保整個系統流程能正常運作。

---

# 測試覆蓋總結

目前測試已涵蓋：

- 規則解析與驗證
- API 取得規則與異常處理
- LINE 訊息發送
- 市場開盤判斷
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