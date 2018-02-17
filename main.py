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

    def get_indicators(self, candles):
        indicators = pd.DataFrame(index = candles.index)
        indicators['macd'] = candles['close'].ewm(span = 12).mean() - candles['close'].ewm(span = 23).mean()
        indicators['macd_signal'] = indicators['macd'].ewm(span = 9).mean()
        indicators['close'] = candles['close']
        return indicators
        
    def get_trend(self, time = 60 * 15):
        candles = self.get_candles(granularity = time)
        indy = self.get_indicators(candles)
        return candles, indy
    
    def get_signal(self, big, small):
        final = pd.DataFrame(index = small.index)
        final['big_signal'] = big['macd'] >= big['macd_signal']
        final['big_signal'] = final['big_signal'].ffill().bfill()
        final['small_signal'] = small['macd'] >= small['macd_signal']
        final['signal'] = final['small_signal'] & final['big_signal']
        return final

    def get_current_signal(self):
        b_candles, big = self.get_trend(int(60 *60))
        s_candles, small = self.get_trend(60*5)
        final = self.get_signal(big, small)
        signal = final['signal']
        return  s_candles, signal
    
    def get_products(self):
        data = pd.DataFrame(self.request('/products'))
        data.set_index('id', inplace = True)
        return data

    def get_open_orders(self):
        return pd.DataFrame(self.request('/orders'))
    
    def place_buy(self, price):
        price = round(price, 2)
        cash_id = self.product_id.split('-')[1]
        coin_id = self.product_id.split('-')[0]        
        
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
        'type':'limit',
        'post_only': True
        }
        self.log('Placing buy Order for amount {:.8f} at price {:.2f} '.format(coin, price))
        return self.request( '/orders' ,json = json ,method = 'POST')

    
    def place_sell(self, price):
        price = round(price, 2)
        cash_id = self.product_id.split('-')[1]
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
                'type':'limit',
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
    

def plot_candles(candles, signal):
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 7)
    def add_rectangle(i, open_, close,low, high, ax, sig):
        x = i - .5
        y = min(open_, close)
        height = abs(open_ - close)
        if sig:
            color = 'green'
            hatch = 'x'
        if not sig:
            color = 'red'
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
    
    
#c, s = aba.get_current_signal()


def main_loop(aba):
    global current_minute
    print('Minute Passed')
    candles, signal = aba.get_current_signal()
    maximum = candles.index.max()
    book = aba.request('/products/{}/book'.format(aba.product_id))
    asks = float(book['asks'][0][0])
    bids = float(book['bids'][0][0])
    
    #price = candles[[low', 'high', 'open', 'close']].ewm(halflife = 2).mean().tail(1).mean().mean()
    s = signal.loc[signal.index.max()]
    
    if s:
        price = min(bids +.01,asks - .01)
        status = aba.place_buy(price)
        if status['status'] == 'rejected':
            print("Order Rejected")
            current_minute = 'rejected'
    if not s:
        price = max(bids +.01,asks - .01)
        status = aba.place_sell(price)
        if status['status'] == 'rejected':
            print("Order Rejected")

            current_minute = 'rejected'
    
    final = pd.DataFrame(index = candles.index)
    
    fig, ax = plt.subplots()
    final = pd.DataFrame(index = candles.index)
    final.loc[signal, 'buy'] = candles.loc[signal, 'close']
    final.loc[~signal, 'sell'] = candles.loc[~signal, 'close']
    plt.scatter(range(len(final)), final['buy'],color = 'green', marker = '.')
    plt.scatter(range(len(final)), final['sell'],color = 'red', marker = '.')
    plt.show()
    
    print(signal.loc[maximum])
    
    
def begin():
    
    current_minute = datetime.now()
    aba = Abathor('LTC-USD')
    
    
    while True:
        now = datetime.now().minute
        if now != current_minute:
            main_loop(aba)
            current_minute = now

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


        

    


#c, s = aba.get_current_signal()
#tester = Tester(c,s)
#tester.do_test()
        
