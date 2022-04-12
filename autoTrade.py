import time
import pyupbit
import datetime
import requests

access = 'access'
secret = 'secret'
myToken = "xoxb-token"

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

KRW_tickers = pyupbit.get_tickers(fiat="KRW")
k = 0.5
bid_tickers = []
bid_price = 100000

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="minute240", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="minute240", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

def get_yesterday_ma5(ticker):
     df = pyupbit.get_ohlcv(ticker)
     close = df['close']
     ma = close.rolling(window=5).mean()
     return ma[-2]

# 자동매매 시작
while True:
    try:
        for tickers in KRW_tickers:
            
            now = datetime.datetime.now()
            start_time = get_start_time(tickers)
            end_time = start_time + datetime.timedelta(hours=3, minutes=50)
            ma5 = get_yesterday_ma5(tickers)

            if start_time < now < end_time:
                target_price = get_target_price(tickers, k)
                current_price = get_current_price(tickers)
                if (target_price < current_price) and (ma5 < current_price):
                    krw = get_balance("KRW")
                    if krw > bid_price:
                        upbit.buy_market_order(tickers, bid_price)
                        KRW_tickers.remove(tickers)
                        post_message(myToken,"#aleart", "{} 매수 완료, 매수 가격 : {}".format(tickers, bid_price))
            else:
                for tickers in KRW_tickers:
                    balance = upbit.get_balance(tickers[tickers.index("-")+1:])
                    if balance * get_current_price(tickers) > 5000:
                        bid_tickers.append(tickers)
                        for tickers in bid_tickers:
                            upbit.sell_market_order(tickers, balance)
                            post_message(myToken,"#aleart", "{} 매도 완료, 매도 가격 : {}".format(tickers, balance))
            time.sleep(1)
    except Exception as e:
        print(e)
        post_message(myToken,"#aleart", e)
        time.sleep(1)
