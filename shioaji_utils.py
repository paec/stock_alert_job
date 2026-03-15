import os
import shioaji as sj
import pandas as pd

# 環境變數管理敏感資訊
SINOPAC_API_KEY = os.getenv("SINOPAC_API_KEY", "")
SINOPAC_SECRET_KEY = os.getenv("SINOPAC_SECRET_KEY", "")
SINOPAC_CA_PATH = os.getenv("SINOPAC_CA_PATH", "Sinopac.pfx")
SINOPAC_CA_PW = os.getenv("SINOPAC_CA_PW", "")
SINOPAC_PERSON_ID = os.getenv("SINOPAC_PERSON_ID", "CY")

_api = None


def init_api():
    global _api
    if _api is not None:
        return _api
    api = sj.Shioaji()
    api.login(SINOPAC_API_KEY, SINOPAC_SECRET_KEY)
    api.activate_ca(
        ca_path=SINOPAC_CA_PATH,
        ca_passwd=SINOPAC_CA_PW,
        person_id=SINOPAC_PERSON_ID,
    )
    _api = api
    return api


def logout_api():
    global _api
    if _api is not None:
        _api.logout()
        _api = None


def get_tw_close_prices(symbol: str, days: int):
    api = init_api()
    # symbol: '0050.TW' -> '0050'
    tw_symbol = symbol.replace('.TW', '')
    contract = api.Contracts.Stocks[tw_symbol]
    # start/end 日期可根據需求調整
    # 這裡用今天往前推 20 天
    import datetime
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=20)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    kbars = api.kbars(contract=contract, start=start, end=end)
    df = pd.DataFrame({**kbars})
    df.ts = pd.to_datetime(df.ts)
    return get_recent_closing_prices(df, days=days)


def get_recent_closing_prices(data_frame, days=3):
    df_temp = data_frame.copy()
    df_temp['Date'] = df_temp.ts.dt.date
    daily_grouped = df_temp.groupby('Date').last()
    result = daily_grouped.tail(days).reset_index()
    return result[['Date', 'Close','ts']]


def format_tw_close_series(close_df):
    close_series = pd.Series(close_df['Close'].values, index=pd.to_datetime(close_df['ts']))
    close_series.index.name = 'Date'
    return close_series
