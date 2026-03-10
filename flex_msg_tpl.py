def build_bubble(symbol, start_date, end_date, x_days, drop, y_percent, history_text):
  triggered = drop <= -float(y_percent)
  # 根據漲跌決定顏色
  if drop > 0:
      drop_color = "#00AA00"    # 正報酬：綠色
  elif triggered:
      drop_color = "#FF5551"    # 跌幅超過閾值：紅色
  else:
      drop_color = "#333333"    # 其他情況：深灰
    
  return {
        "type": "bubble",
        "header": {
          "type": "box",
          "layout": "vertical",
          "contents": [
            {
              "type": "text",
              "text": f"📊 {symbol} 股票報表",
              "weight": "bold",
              "size": "lg"
            }
          ]
        },
        "body": {
          "type": "box",
          "layout": "vertical",
          "contents": [
            {
              "type": "text",
              "text": f"📅 {start_date} ~ {end_date}",
              "size": "sm",
              "color": "#888888"
            },
            {
              "type": "separator",
              "margin": "md"
            },
            {
              "type": "box",
              "layout": "vertical",
              "margin": "md",
              "contents": [
                {
                  "type": "text",
                  "text": "收盤價歷史",
                  "weight": "bold",
                  "size": "sm",
                  "margin": "sm"
                },
                {
                  "type": "text",
                  "text": history_text,
                  "size": "xs",
                  "color": "#555555",
                  "wrap": True
                }
              ]
            },
            {
              "type": "box",
              "layout": "vertical",
              "margin": "lg",
              "paddingAll": "10px",
              "backgroundColor": "#F0F0F0",
              "cornerRadius": "md",
              "contents": [
                {
                  "type": "text",
                  "text": f"({x_days}日)內漲跌幅: {drop:.2f}%",
                  "size": "sm",
                  "color": drop_color,
                  "weight": "bold"
                },
                {
                  "type": "text",
                  "text": f"⚠️ 警示觸發 (閾值 -{y_percent}%)" if triggered else f"未觸發 (閾值 -{y_percent}%)",
                  "size": "xxs",
                  "color": "#FF5551" if triggered else "#AAAAAA"
                }
              ]
            }
          ]
        }
  }


def build_carousel(bubbles):
  return {
    "type": "carousel",
    "contents": bubbles
  }
