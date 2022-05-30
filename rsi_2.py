import time
import pyupbit
import datetime
import requests
import pandas as pd
import numpy as np

access = 'a'
secret = 'b'
myToken = "xoxb-c"

bid_price = 5000
fee = 0.0005
KRW_tickers = pyupbit.get_tickers(fiat="KRW")
period = 14
itv = "day"

# day/minute1/minute3/minute5/minute10/minute15/minute30/minute60/minute240/week/month

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+ token},
        data={"channel": channel,"text": text}
    )

# 로그인
upbit = pyupbit.Upbit(access, secret)

# 시작 메세지 슬랙 전송
post_message(myToken,"#aleart", "autotrade start")
print("start auto Trade")

# 잔고 조회
def get_balance(ticker):
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

# 시작 시간
def get_start_time(ticker):
    df = pyupbit.get_ohlcv(ticker, interval=itv, count = 1)
    start_time = df.index[0]
    return start_time

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

# 매수 주문
def buy_order(ticker, price, rsi, revenue):
    upbit.buy_market_order(ticker, price)
    post_message(myToken,"#aleart", "{} 매수 완료".format(ticker))
    post_message(myToken,"#aleart", "매수 가격 : {}".format(price))
    post_message(myToken,"#aleart", "RSI : {}".format(rsi))
    post_message(myToken,"#aleart", "손익 : {}".format(revenue))
    #print("{} 매수 완료, 매수 가격 : {}, RSI : {}".format(ticker, price, rsi))
    return 0

# 매도 주문
def sell_order(ticker, price, sell_price, rsi, revenue):
    upbit.sell_market_order(ticker, price)
    post_message(myToken,"#aleart", "{} 매도 완료".format(ticker))
    post_message(myToken,"#aleart", "매도 가격 : {}".format(int(sell_price)))
    post_message(myToken,"#aleart", "RSI : {}".format(rsi))
    post_message(myToken,"#aleart", "손익 : {}".format(revenue))
    #print("{} 매도 완료, 매도 가격 : {}, RSI : {}".format(ticker, int(sell_price), rsi))
    return 0


# 자동매매 시작
while True:
    try:
        start_time = get_start_time("KRW-BTC") + datetime.timedelta(minutes = 0.1)
        end_time = start_time + datetime.timedelta(minutes = 1)
        now = datetime.datetime.now()
        print(start_time, end_time, now)
        time.sleep(1)
        if start_time < now < end_time:
            post_message(myToken,"#aleart", "거래조건 검색중")
            for tickers in KRW_tickers:
                
                print("{} 거래 조건 검색중".format(tickers))
                balance = upbit.get_balance(tickers[tickers.index("-") +1:])

                df = pyupbit.get_ohlcv(tickers, interval = itv)
                df['diff'] = df['close'] - df['close'].shift(1)
                df['u'] = np.where(df['diff']>0, df['diff'], 0)
                df['d'] = np.where(df['diff']<0, df['diff'], 0)
                df['au'] = df['u'].ewm(com=(period - 1), min_periods=period).mean()
                df['ad'] = df['d'].abs().ewm(com=(period - 1), min_periods=period).mean()
                df['RS'] = df['au'] / df['ad']
                df['RSI'] = pd.Series(100 - (100 / (1 + df['RS'])))
                df['buyPrice'] = np.where((df['RSI'] <= 30) & (df['RSI'].shift(1) < df['RSI'].shift(2)), df['open'], 0)
                df['sellPrice'] = np.where((df['RSI'].shift(1) >= 70) & (df['RSI'].shift(1) < df['RSI'].shift(2)), df['open'], 0)
                df['isBuy']= np.where(df['buyPrice'] > 0, 1, 0)
                df['isSell']= np.where(df['sellPrice'] > 0, 1, 0)
                df['sellCount']= df['isSell'].cumsum()
                df['buyCount'] = df['isBuy'].groupby(df['sellCount']).cumsum()
                df['BQ'] = np.where(df['isBuy'] == 1 , bid_price / df['buyPrice'], 0)
                df['HQ'] = df['BQ'].groupby(df['sellCount']).cumsum()
                df['revenue'] = np.where((df['buyCount'].shift(1) >= 1) & (df['buyCount'] == 0), ((df['sellPrice'] * df['HQ'].shift(1)) * (1 - fee)) - (bid_price * df['buyCount'].shift(1)), 0)

                rsi_d = df['RSI'][-2:-1]
                rsi_d1 = df['RSI'][-3:-2]
                revenue = df['revenue'][-1:]
                print(rsi_d.values, rsi_d1.values, revenue.values)

                if rsi_d.values <= 30 and (rsi_d.values < rsi_d1.values):
                    buy_order(tickers, bid_price, rsi_d.values, revenue.values)

                elif rsi_d1.values >= 70 and (rsi_d.values < rsi_d1.values):
                    ticker_balance = balance * get_current_price(tickers)
                    if ticker_balance >= 5000:
                        sell_order(tickers, balance, ticker_balance, rsi_d.values, revenue.values)
                time.sleep(1)

    except Exception as e:
        print(e)
        post_message(myToken,"#aleart", e)
        time.sleep(1)
