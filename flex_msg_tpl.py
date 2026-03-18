def _format_close_value(value):
  if value is None:
      return "N/A"
  return f"{float(value):.2f}"


def _format_pct_value(value):
  if value is None:
      return "N/A"
  return f"{float(value):.2f}%"


def _format_date_value(value):
  if value is None:
      return "N/A"
  return str(value)


def _resolve_drop_color(drop, threshold):
  if drop is None:
      return "#333333"
  if drop > 0:
      return "#00AA00"
  if threshold is not None and drop <= -float(threshold):
      return "#FF5551"
  return "#333333"


def _build_trigger_text(drop, threshold):
  if drop is not None and threshold is not None and drop <= -float(threshold):
      return f"⚠️ 警示觸發 (閾值 -{threshold}%)", "#FF5551"
  return f"未觸發 (閾值 -{threshold}%)", "#AAAAAA"


def build_bubble(
  symbol,
  start_date,
  end_date,
  x_days,
  drop,
  y_percent,
  history_text,
  is_final_report: bool = False,
  short_lookback_days=None,
  long_lookback_days=None,
  short_lookback_change_pct=None,
  long_lookback_change_pct=None,
  short_lookback_date=None,
  long_lookback_date=None,
  close_short_lookback_ago=None,
  close_long_lookback_ago=None,
  long_term_drop_percent=None,
):
  short_drop_color = _resolve_drop_color(short_lookback_change_pct, y_percent)
  long_drop_color = _resolve_drop_color(long_lookback_change_pct, long_term_drop_percent)
  short_trigger_text, short_trigger_color = _build_trigger_text(short_lookback_change_pct, y_percent)
  long_trigger_text, long_trigger_color = _build_trigger_text(long_lookback_change_pct, long_term_drop_percent)
    
  # 標題文字：如果是 final report，就加上 (已關盤)
  title_suffix = " (已關盤)" if is_final_report else ""
  title_text = f"📊 {symbol} 股票報表{title_suffix}"

  return {
        "type": "bubble",
        "header": {
          "type": "box",
          "layout": "vertical",
          "contents": [
            {
              "type": "text",
              "text": title_text,
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
              "size": "md",
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
                  "size": "md",
                  "margin": "sm"
                },
                {
                  "type": "text",
                  "text": history_text,
                  "size": "md",
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
                  "text": f"({short_lookback_days}日內)漲跌幅: {_format_pct_value(short_lookback_change_pct)}",
                  "size": "sm",
                  "color": short_drop_color,
                  "weight": "bold"
                },
                {
                  "type": "text",
                  "text": f"{short_lookback_days} days ago ({_format_date_value(short_lookback_date)}) close: {_format_close_value(close_short_lookback_ago)}",
                  "size": "xs",
                  "color": "#666666",
                  "margin": "sm"
                },
                {
                  "type": "text",
                  "text": short_trigger_text,
                  "size": "xs",
                  "color": short_trigger_color,
                  "margin": "sm"
                },
                {
                  "type": "separator",
                  "margin": "md"
                },
                {
                  "type": "text",
                  "text": f"({long_lookback_days}日內)漲跌幅: {_format_pct_value(long_lookback_change_pct)}",
                  "size": "sm",
                  "color": long_drop_color,
                  "weight": "bold",
                  "margin": "md"
                },
                {
                  "type": "text",
                  "text": f"{long_lookback_days} days ago ({_format_date_value(long_lookback_date)}) close: {_format_close_value(close_long_lookback_ago)}",
                  "size": "xs",
                  "color": "#666666"
                },
                {
                  "type": "text",
                  "text": long_trigger_text,
                  "size": "xs",
                  "color": long_trigger_color,
                  "margin": "sm"
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
