import pandas as pd
import glob
from rack import Equipment
import pickle
import os

def load_results():
    files = glob.glob('Publications\*.result')
    for name in files:
        with open(name, 'rb') as f:
            ans = pickle.load(f)
        os.remove(name)
        name = name.replace('Publications\\', '')
        name.replace('.result', '')
        
        yield ans, name
    




class Analyst():
    cash = None
    cost = None
    trade_count = None
    trades = None
    i = None
    def __init__(self):
        self.cash = pd.DataFrame()
        self.cost = pd.DataFrame()
        self.trade_count = pd.DataFrame()
        self.trades = {}
        self.i = 0
        
    def enter_results(self):
        i = self.i
        self.trades[i] = {}
        
        for study, name in load_results():
            self.cash.loc[i,name] = study.cash
            self.cost.loc[i, name] = study.cost
            self.trade_count.loc[i, name] = study.trades
            self.trades[i][name] = study.trade_history
        self.i = len(self.cash)
        
        return 

    def get_parcel(self):
        self.enter_results()
        parcel = {'cash':self.cash, 
                  'cost':self.cost,
                  'trade_count':self.trade_count,
                  'trades':self.trades
                  }
        return parcel
        



