from datetime import datetime
import os
import time
import requests
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import doctor
import math
import matplotlib.patches as patches
import matplotlib as mpl

def round(number, ndigits):
    x = number * (10** ndigits )
    x = float(math.floor(x))
    x = x/(10**ndigits)
    return x


class Abathor():
    url = 'https://api.gdax.com'
    product_id = None
    logfile = None
    last_message = None
    
    def __init__(self, product_id):
        self.product_id = product_id
        self.last_message = datetime.now()
        self.logfile = os.getcwd() + '\\logs\\ {} '.format(datetime.today().strftime('%b %d %Y')) + product_id + '.txt'
        products = self.get_products()
        self.min_size = float(products.loc[product_id, 'base_min_size'])
    def log(self, message):
        print(message)
        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        with open(self.logfile, "w") as f:
            f.write(message)
        return
    
    def request(self, path, params=None, json = None, method = 'GET'):
        #Requests passthrough, tries to avoid the too many requests code by adding pauses
        self.last_message
        now = datetime.now()
        if (now - self.last_message).total_seconds() <= 1:
            time.sleep(1)
        try:
            done = False
            while not done:
                r = requests.request(method,self.url + path, params=params, json = json , auth = doctor.get_auth(), timeout=30)
                if r.status_code == 429:
                    time.sleep(2)
                    pass
                if r.status_code != 429:
                    done = True
        except ConnectionError as e:
            message = datetime.now().isoformat() + ' -----\n'
            message = message + 'CONNECTIONERROR\n'
            message = message + repr(e)
            self.log(message)
            raise
            
    
        self.r = r
        if r.status_code != 200:
            message = datetime.now().isoformat()+ ' ---- '
            message = message + 'staus_code: {}'.format(r.status_code)
            message = message + 'reason: {}'.format(r.reason)
            message = message + 'text: {}\n'.format(r.text)
            self.log( message  )
        self.last_message = datetime.now()
        return r.json()
        
    def get_candles(self, start=None, end=None, granularity=None):
        #Downloads new candles, will not put them in sql,just give it a local start and end time in with a granualrity in seconds 
        params = {}
        if start is not None:
            start = start + self.time_difference
            params['start'] = start.isoformat()
        if end is not None:
            end = end + self.time_difference
            params['end'] = end.isoformat()
        if granularity is not None:
            params['granularity'] = granularity
        candles = self.request('/products/{}/candles'.format(str(self.product_id)), params=params)
        candles = pd.DataFrame(candles, columns = [ 'time', 'low', 'high', 'open', 'close', 'volume' ])
        candles['timestamp'] = candles['time']
        candles['time'] = candles['time'].apply(datetime.fromtimestamp)
        candles.sort_values('time', inplace= True)
        candles.set_index('time', inplace= True)
        return candles
    
    def get_macd(self, candles, long = 23, short = 12, signal = 9 ):
        macd = pd.DataFrame(index = candles.index)
        macd['macd'] = candles['close'].ewm(span = short).mean() - candles['close'].ewm(span = long).mean()
        macd['macd_signal'] = macd['macd'].ewm(span = signal).mean()
        macd['close'] = candles['close']
        return macd
        
    def get_rsi(self, prices, time_period = 14):
        delta = prices.diff()
        dUp, dDown = delta.copy(), delta.copy()
        dUp[dUp < 0] = 0
        dDown[dDown > 0] = 0
        
        RolUp = dUp.rolling(window = time_period, center = False).mean()
        RolDown = dDown.rolling(window = time_period, center = False).mean().abs()
        
        RS = RolUp / RolDown
        rsi= 100.0 - (100.0 / (1.0 + RS))
        return rsi


    def get_products(self):
        data = pd.DataFrame(self.request('/products'))
        data.set_index('id', inplace = True)
        return data

    def get_open_orders(self):
        return pd.DataFrame(self.request('/orders'))
    
    def place_buy(self, price, _type = 'limit'):
        price = round(price, 2)
        cash_id = self.product_id.split('-')[1]
        #coin_id = self.product_id.split('-')[0]        
        
        balance = self.clear_holds()

        cash = round(balance.loc[cash_id, 'balance'],2)
        if cash <= 0.01:
            return {'status':'No money to buy with'}
        coin = cash/price
        json = {
        'price': '{:.2f}'.format(price),
        'size': '{:.8f}'.format(coin),
        'side': 'buy',
        'product_id':self.product_id,
        'type':_type,
        'post_only': True
        }
        self.log('Placing buy Order for amount {:.8f} at price {:.2f} '.format(coin, price))
        return self.request( '/orders' ,json = json ,method = 'POST')

    
    def place_sell(self, price, _type = 'limit'):
        price = round(price, 2)
        #cash_id = self.product_id.split('-')[1]
        coin_id = self.product_id.split('-')[0]
        balance = self.clear_holds()

        coin = round(balance.loc[coin_id, 'balance'], 8)
        if coin < self.min_size:
            return {'status':'Nothing to sell'}
        json = {
                'price': '{:.2f}'.format(price),
                'size': '{:.8f}'.format(coin),
                'side': 'sell',
                'product_id':self.product_id,
                'type':_type,
                'post_only': True
                }
        self.log('Placing sell Order for amount {:.8f} at price {:.2f} '.format(coin, price))
        return self.request( '/orders' ,json = json ,method = 'POST')
        
    def clear_holds(self ):
        while True:
            balance =  pd.DataFrame(self.request('/accounts'))
            balance.set_index('currency', inplace = True)

            for column in ['available', 'balance', 'hold']:
                balance[column] = pd.to_numeric(balance[column])
                
            holds = balance['hold']
            
            if holds.sum() > 0:
                self.log('--- clearing Holds --- ')
                self.log(str(self.cancel_all()))
            if holds.sum() == 0:
                return balance
    
    def cancel_all(self, order_id = 'None'):
        if order_id == 'None':
            return self.request('/orders', method = 'DELETE')
        if order_id != 'None':
            if type(order_id) == str:
                return self.request('/orders/{}'.format(order_id), method = 'DELETE')
            results = []
            for iden in order_id:
                results.append(self.request('/orders/{}'.format(iden), method = 'DELETE'))
            return results
    

    def get_book(self, level = 1):
        x = self.request('/products/{}/book'.format(self.product_id), params= {'level':level})
        asks = pd.DataFrame(x['asks'], columns = ['price', 'size', 'count'])
        bids = pd.DataFrame(x['bids'], columns = ['price', 'size', 'count'])
        for data in asks, bids:
            for column in data.columns:
                data[column] = pd.to_numeric(data[column])
        bids.set_index('price', inplace = True)
        asks.set_index('price', inplace = True)
        return bids, asks

def plot_candles(candles, signal):
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 7)
    def add_rectangle(i, open_, close,low, high, ax, sig):
        x = i - .5
        y = min(open_, close)
        height = abs(open_ - close)
        if sig == 'buy':
            color = 'green'
            hatch = 'x'
        if sig == 'sell':
            color = 'red'
            hatch = ''
            
        if sig == 'wait':
            color = 'orange'
            hatch = ''
        ax.add_patch(patches.Rectangle((x, y), .9, height,
                                       fill = open_ <= close, facecolor = color,
                                       edgecolor = color, hatch = hatch ))
        top = max(open_,close)
        bottom = min(open_,close)

        if low < bottom:
            ax.add_line(mpl.lines.Line2D([i,i], [low, bottom], color = color) )

            
        if high > top:
            ax.add_line(mpl.lines.Line2D([i,i], [high, top], color = color) )

        
    for i, index in enumerate(candles.index):
        sig = signal.loc[index]
        row = candles.loc[index]
        add_rectangle(i, row['open'], row['close'],row['low'], row['high'],  ax, sig)
    ax.set_xlim(0, len(candles))
    ax.set_ylim(candles['close'].min() *.998, candles['close'].max() * 1.002)
    plt.show()


def main_loop(strategy):
    global current_minute
    aba = strategy.aba
    candles, signal = strategy.get_signal()
    maximum = candles.index.max()
    book = aba.request('/products/{}/book'.format(aba.product_id))
    
    s = signal.loc[maximum]
    if s == 'buy':
        price = strategy.get_price(book, kind = 'buy')
        print('sell {}'.format(price))
        #status = aba.place_buy(price, strategy.get_order_type(kind = 'buy'))
        #if status['status'] == 'rejected':
        #    print("Order Rejected")
        #    current_minute = 'rejected'
            
    if s == 'sell':
        price = strategy.get_price(book, kind = 'sell')
        print('sell {}'.format(price))
        #status = aba.place_sell(price, strategy.get_order_type(kind = 'sell'))
        #if status['status'] == 'rejected':
        #    print("Order Rejected")
        #    current_minute = 'rejected'

    strategy.plot()

class RSI_and_MACD_strategy():
    aba = None
    signals = {}
    
    def __init__(self, product_id):
        self.aba = Abathor(product_id)        
        
    def get_signal(self):
        candles = self.aba.get_candles(granularity=60)
        long_candles = self.aba.get_candles(granularity = 15* 60)
        
        rsi = self.aba.get_rsi(candles['close'])

        macd = self.aba.get_macd(long_candles,  23, 13, 9 )
        temp = pd.DataFrame(index = candles.index)
        temp['macd'] = macd['macd_signal'] < macd['macd']
        temp = temp.ffill()
        temp = temp.bfill()
        macd_mask = temp['macd']
        
        
        final = pd.Series(index = rsi.index)
        final.loc[rsi.isnull()] = 'wait'
        final.loc[rsi <= 30] = 'buy'
        final.loc[rsi >= 70] = 'sell'
        final.loc[final.isnull()] = 'wait'
        final.loc[~macd_mask] = 'sell'
        
        self.signals['rsi'] = rsi
        self.signals['macd'] = macd
        self.signals['color'] = final
        self.signals['candles'] = candles
        
        return candles, final

    def get_order_type(self, kind):
        if kind == 'buy':
            return 'limit'
        
        if kind == 'sell':
            return 'limit'
            
    def get_price(self, book = None, kind = 'buy'):
        if type(book) == type(None):
            book = self.aba.request('/products/{}/book'.format(self.aba.product_id))
            
        asks = float(book['asks'][0][0])
        bids = float(book['bids'][0][0])
        
        if kind == 'sell':
            return max(bids +.01,asks - .01)
        if kind == 'buy':
            return min(bids +.01,asks - .01)
    
    def plot(self):

        rsi = self.signals['rsi']
        macd = self.signals['macd']
        macd = macd[macd.index >= rsi.index.min()]
        fig, ax = plt.subplots()
        fig.set_size_inches(9, 7)
        rsi.plot(ax = ax)
        
        ax2 = ax.twinx()
        macd[['macd', 'macd_signal']].plot(ax = ax2)
        plt.show()
        plot_candles(self.signals['candles'], self.signals['color'])
        
        
        

class MACD_strategy():
    aba = None
    signals = {}
    def __init__(self, product_id):
        self.aba = Abathor(product_id)
    
    def get_signal(self):
        short_candles = self.aba.get_candles(granularity=60 * 5)
        macd = self.aba.get_macd(short_candles)
        self.signals['macd'] = macd
        return short_candles, macd['macd_signal'] < macd['macd']
    
    def get_order_type(self, kind):
        if kind == 'buy':
            return 'market'
        
        if kind == 'sell':
            return 'limit'
            
    
    def get_price(self, book = None, kind = 'buy'):
        if type(book) == type(None):
            book = self.aba.request('/products/{}/book'.format(self.aba.product_id))
            
        asks = float(book['asks'][0][0])
        bids = float(book['bids'][0][0])
        
        if kind == 'sell':
            return max(bids +.01,asks - .01)
        if kind == 'buy':
            return min(bids +.01,asks - .01)
        

    def plot(self):

        macd = self.signals['macd']
        fig, ax = plt.subplots()
        
        macd[['macd', 'macd_signal']].plot(ax = ax)
        ax2 = ax.twinx()
        macd['close'].plot(ax2)


def begin():
    strategy = RSI_and_MACD_strategy('LTC-BTC')
    current_minute = datetime.now()

    
    while True:
        now = datetime.now().minute
        if now != current_minute:
            main_loop(strategy)
            current_minute = now



def chart_rsi(aba):
    c = aba.get_candles()
    rsi = aba.get_rsi(c['close'], 32)
    fig, ax = plt.subplots()
    c['close'].plot(ax = ax)
    ax2 = ax.twinx()
    rsi.plot(ax = ax2, color = 'green')
    plt.show()



class Tester():
    cash = None
    coin = None
    def __init__(self, candles, signal, cash = 100, coin = 0):
        self.cash = cash
        self.coin = coin
        self.candles = candles
        self.signal = signal
    
    def buy(self, price):
        self.coin = self.coin + (self.cash/price)
        self.cash = 0
        
    def sell(self, price):        
        self.cash = self.cash + (price * self.coin)
        self.coin = 0
        
    
    def do_test(self):
        candles = self.candles
        for index in candles.index:
            price = candles.loc[index, 'close']
            sign = self.signal.loc[index]
            if sign and self.coin == 0:
                self.buy(price)
            if (not sign) and self.cash == 0:
               self.sell(price)
        self.sell(price)
        print('Gains From Trading {}'.format(self.cash - 100))
        
        self.cash = 100
        self.buy(candles.iloc[0]['close'])
        self.sell(candles.iloc[len(candles)-1]['close'])
        
        print('Gains From Buy and Hold {}'.format(self.cash - 100))
        fig, ax = plt.subplots()
        fig.set_size_inches(8, 6)
        final = pd.DataFrame(index = candles.index)
        final.loc[self.signal, 'buy'] = candles.loc[self.signal, 'close']
        final.loc[~self.signal, 'sell'] = candles.loc[~self.signal, 'close']
        plt.scatter(range(len(final)), final['buy'],color = 'green')
        plt.scatter(range(len(final)), final['sell'],color = 'red')


        


        
