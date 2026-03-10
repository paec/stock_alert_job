import sys
import yfinance as yf
from check_stock import check_stock

def main():
    # 測試參數
    symbol = "AAPL"  # 可替換成其他股票代碼
    x_days = 5
    y_percent = 3.0
    check_stock(symbol, x_days, y_percent)

if __name__ == "__main__":
    main()
