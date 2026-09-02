# Stock Alert 決策流程

本圖依目前 [check_stock.py](check_stock.py) 的 `build_stock_bubble()`、`_should_send_report()`，以及 [flex_msg_tpl.py](flex_msg_tpl.py) 的 `build_bubble()` 整理。

```mermaid
flowchart TD
    A([開始 build_stock_bubble]) --> B[取得市場時區與現在時間]
    B --> C{FORCE_SEND_REPORT}
    C -- 否 --> D{市場開放}
    D -- 否 --> R1([return None])
    D -- 是 --> E[下載 close prices]
    C -- 是 --> E

    E --> F{FORCE_SEND_REPORT}
    F -- 否 --> G{最後一筆是今天資料}
    G -- 否 --> R2([return None])
    G -- 是 --> H{資料量足夠}
    F -- 是 --> H
    H -- 否 --> R3([return None])
    H -- 是 --> I[計算 short_drop / long_drop<br/>判定 short、long、final]

    I --> J{FORCE 或 short 或 long 或 final}
    J -- 否 --> R4[記錄未觸發訊息<br/>return None]
    J -- 是 --> K[has_alert_trigger = short 或 long]
    K --> L[check_add_more_status]

    L --> M{threshold 觸發<br/>且已加碼<br/>且非 final、非 force}
    M -- 是 --> R5[跳過 LINE alarm<br/>return None]
    M -- 否 --> N[建立報表資料並記錄狀態]

    N --> O{has_alert_trigger 或已加碼}
    O -- 否 --> P[show_add_more_button = false]
    O -- 是 --> Q[show_add_more_button = true]
    P --> S[呼叫 build_bubble]
    Q --> S

    S --> T{show_add_more_button}
    T -- 否 --> U[不建立 footer button]
    T -- 是 --> V{add_more_already_added}
    V -- 否 --> W[建立 primary button]
    V -- 是 --> X[建立 secondary button<br/>label: 已加碼]

    U --> Y([return bubble])
    W --> Y
    X --> Y
```

## 判斷重點

- `FORCE_SEND_REPORT`、threshold 觸發、final report 任一成立時，才會進入後續報表流程並查詢加碼狀態。
- 只有一般的 threshold alarm，且已加碼、不是 final、也不是 force 時，才會跳過 alarm。
- 按鈕顯示條件是 `has_alert_trigger or add_more_already_added`，不直接使用 `is_final_report` 或 `FORCE_SEND_REPORT` 判斷。
- `add_more_already_added` 為 `true` 時，按鈕使用 `secondary`／「已加碼」樣式；為 `false` 時，若因 threshold 顯示按鈕，使用 `primary` 樣式。