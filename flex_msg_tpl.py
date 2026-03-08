def build_bubble(symbol, start_date, end_date, x_days, drop, y_percent, history_text):
  triggered = drop <= -float(y_percent)
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
              "size": "xs",
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
                  "color": "#FF5551" if triggered else "#333333",
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