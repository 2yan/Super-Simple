
import pandas as pd


class Equipment():
    cash = None
    coin = None
    position = None
    trades = None
    cost = None
    trade_history = None
    stoploss = None
    buy_price = None
    target_percent = None
    
    def __init__(self, cash = 100, coin = 0, position = 'out', stoploss = False, target_percent = False):
        assert(position in ('in', 'out'))
        self.cash = cash
        self.coin = coin
        self.position = position
        self.trades = 0
        self.trade_history = []
        self.cost = 0
        self.stoploss = stoploss
        self.target_percent = target_percent
        
    def sell(self, p):
        if self.position == 'out':
            return 
        self.cash = self.coin * p
        self.cost = self.cost + (0.003 * self.cash)
        self.coin = 0
        self.position = 'out'
        self.trades = self.trades + 1
        spot = len(self.trade_history) - 1
        self.trade_history[spot] = (self.cash - self.trade_history[spot])/self.trade_history[spot]
        
        return 
    
    def buy(self, p):
        if self.position == 'in':
            return
        self.trade_history.append(self.cash)
        self.coin = self.cash/p
        self.cost = self.cost + (0.003 * self.cash)
        self.cash = 0
        self.position = 'in'
        self.trades = self.trades + 1
        self.buy_price = p
        return
        

    def test_signal(self, prices, signal):
        for i in range(len(signal)):
            p = prices.iloc[i]
            s = signal.iloc[i]
            
            if (self.stoploss != False) and (self.position) == 'in':
                if p <= ((1 - self.stoploss) * self.buy_price):                   
                    s = 'sell'
            if (self.target_percent != False) and (self.position) == 'in':
                if p >= ((1 + self.target_percent) * self.buy_price):
                    s = 'sell'
                    
            if s == 'sell':
                self.sell(p)
                
            if s == 'buy':
                self.buy(p)
            if s == 'hold':
                s = 'hold'
                
        self.sell(p)
        return self.cash, self.coin, self.trades
    
    def __str__(self):
        text = 'Trades {:,.0f} | Cash $ {:.2f} | Cost $ {:,.2f}'.format(self.trades, self.cash, self.cost )
        return text
        
    def get_sharpe(self):
        hist = pd.Series(self.trade_history)
        hist = hist[hist <0] 
        returns = (self.cash - 100)/100
        return returns/hist.apply(abs).mean()
