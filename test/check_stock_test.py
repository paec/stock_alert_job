import yfinance as yf

def check_stock(symbol, x_days, y_percent):
    data = yf.download(symbol, period=f"{x_days+5}d", progress=False, auto_adjust=False)

    if len(data) < x_days + 1:
        print(f"{symbol}: not enough data")
        return
    print(data["Close"])
    today = float(data["Close"].iloc[-1].item())
    past = float(data["Close"].iloc[-(x_days)].item())
    print(f"{symbol} today: {today}, {x_days} days ago: {past}")
    drop = (today - past) / past * 100

    if drop <= -float(y_percent):
        msg = f"{symbol}: {drop:.2f}% in {x_days} days (threshold: {y_percent}%)"
        print(msg)
    else:
        print(f"{symbol}: {drop:.2f}% in {x_days} days (threshold: {y_percent}%) - not triggered")


def main():
    # 測試參數
    x_days = 5
    y_percent = 3
    stocks = ["00692.TW","VOO"]

    for symbol in stocks:
        check_stock(symbol, x_days, y_percent)


if __name__ == "__main__":
    main()
