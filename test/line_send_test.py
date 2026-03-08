import argparse
import datetime as dt
import os

import requests

LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
LINE_TOKEN = "EYJGVyVhwW9p7/hpuna9PZOpooG6tZnfWkvv755YGPl6R2DZGNWgvuKXAGzUkSW6D2MORSCkKK2n+yOB1MllPF1aWOtxsuEHKJy3NeRy0GrYEC5OginfWXyHz4kS/dDZ1YRw5F40YF7LkKwV1tB6GAdB04t89/1O/w1cDnyilFU="


def send_line_broadcast(token: str, message: str) -> tuple[int, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {
                "type": "flex",
                "altText": "股票報表顯示失敗",
                "contents": message  # 這裡直接傳入 bubble 的內容
            }
        ]
    }

    response = requests.post(
        LINE_BROADCAST_URL,
        headers=headers,
        json=payload,
        timeout=20,
    )
    return response.status_code, response.text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MVP: Send one test message via LINE broadcast API."
    )
    parser.add_argument(
        "--message",
        default=f"[MVP TEST] LINE message test at {dt.datetime.now().isoformat(timespec='seconds')}",
        help="Text message to send.",
    )
    parser.add_argument(
        "--token",
        default=LINE_TOKEN,
        help="LINE channel access token. Defaults to LINE_TOKEN env.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    token = args.token.strip()
    if not token:
        print("LINE token missing. Set LINE_TOKEN or pass --token.")
        raise SystemExit(1)

    message_dict = {
  "type": "carousel",
  "contents": [
    {
      "type": "bubble",
      "header": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "text",
            "text": "📊 VOO 股票報表",
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
            "text": "📅 2026-02-23 ~ 03-06",
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
                "text": "02-23: 627.63  02-24: 632.21\n02-25: 637.53  02-26: 633.95\n02-27: 631.04  03-02: 631.28\n03-03: 625.72  03-04: 630.18\n03-05: 626.81  03-06: 618.43",
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
                "text": "今日跌幅: -2.04%",
                "size": "sm",
                "color": "#FF5551",
                "weight": "bold"
              },
              {
                "type": "text",
                "text": "警示未觸發 (閾值 3%)",
                "size": "xxs",
                "color": "#AAAAAA"
              }
            ]
          }
        ]
      }
    },
    {
      "type": "bubble",
      "header": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "text",
            "text": "📊 VT 股票報表",
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
            "text": "📅 2026-02-23 ~ 03-06",
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
                "text": "02-23: 627.63  02-24: 632.21\n02-25: 637.53  02-26: 633.95\n02-27: 631.04  03-02: 631.28\n03-03: 625.72  03-04: 630.18\n03-05: 626.81  03-06: 618.43",
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
                "text": "今日跌幅: -2.04%",
                "size": "sm",
                "color": "#FF5551",
                "weight": "bold"
              },
              {
                "type": "text",
                "text": "警示未觸發 (閾值 3%)",
                "size": "xxs",
                "color": "#AAAAAA"
              }
            ]
          }
        ]
      }
    }
  ]
}
    status_code, body = send_line_broadcast(token, message_dict)
    print(f"HTTP {status_code}")

    if status_code < 400:
        print("LINE send success.")
    else:
        print("LINE send failed.")
        print(body)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
