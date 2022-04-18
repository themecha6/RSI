from re import I
import time
import pyupbit
import datetime
import requests
import pandas as pd
import numpy as np

access = 'a'
secret = 'b'
myToken = "xoxb-c"

bid_price = 1000
KRW_tickers = pyupbit.get_tickers(fiat="KRW")
period = 14

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
    df = pyupbit.get_ohlcv(ticker, interval="minute240", count=1)
    start_time = df.index[0]
    return start_time

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

# 매수 주문
def buy_order(ticker, price, rsi):
    upbit.buy_market_order(ticker, price)
    post_message(myToken,"#aleart", "{} 매수 완료, 매수 가격 : {}, RSI : ".format(ticker, price, rsi))
    print("{} 매수 완료".format(ticker))
    return 0

# 매도 주문
def sell_order(ticker, price, sell_price, rsi):
    upbit.sell_market_order(ticker, price)
    post_message(myToken,"#aleart", "{} 매도 완료, 매도 가격 : {}, RSI : ".format(ticker, int(sell_price), rsi))
    print("{} 매도 완료".format(ticker))
    return 0


# 자동매매 시작
while True:
    try:
        start_time = get_start_time("KRW-BTC") + datetime.timedelta(hours=4, minutes=0.5)
        end_time = start_time + datetime.timedelta(minutes=1.5)
        now = datetime.datetime.now()
        print(start_time, end_time, now)
        time.sleep(30)
        if start_time < now < end_time:
            post_message(myToken,"#aleart", "거래조건 검색중")
            for tickers in KRW_tickers:
                
                print("{} 거래 조건 검색중".format(tickers))
                balance = upbit.get_balance(tickers[tickers.index("-") +1:])

                df = pyupbit.get_ohlcv(tickers)
                df['diff'] = df['close'] - df['close'].shift(1)
                df['u'] = np.where(df['diff']>0, df['diff'], 0)
                df['d'] = np.where(df['diff']<0, df['diff'], 0)
                df['au'] = df['u'].ewm(com=(period - 1), min_periods=period).mean()
                df['ad'] = df['d'].abs().ewm(com=(period - 1), min_periods=period).mean()
                df['RS'] = df['au'] / df['ad']
                df['RSI'] = pd.Series(100 - (100 / (1 + df['RS'])))
                
                rsi_d = df['RSI'][-1:]
                rsi_d1 = df['RSI'][-2:-1]

                if rsi_d <= 30 and rsi_d < rsi_d1:
                    buy_order(tickers, bid_price, rsi_d)

                if rsi_d <= 50 and rsi_d1 > 50:
                    i = 1
                    while True:
                        i += 1
                        rsi = df['RSI'][-i:-i+1]
                        time.sleep(0.1)
                        if rsi.values >= 70:
                            buy_order(tickers, bid_price, rsi_d)
                            break
                        elif rsi.values <= 50:
                            break

                if rsi_d <= 70 and rsi_d1 >= 70:
                    ticker_balance = balance * get_current_price(tickers)
                    if ticker_balance >= 5000:
                        sell_order(tickers, balance, ticker_balance, rsi_d)
                time.sleep(1)

    except Exception as e:
        print(e)
        post_message(myToken,"#aleart", e)
        time.sleep(10)
