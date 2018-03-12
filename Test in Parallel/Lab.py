import os
import pickle
import pandas as pd
import glob
from subprocess import Popen, PIPE
import multiprocessing as multi
import time

class Intern():
    ''' The Strategy Argument is a function that works with a the dataframes found in raw_data.
    It Labels each position as hold, buy and sell '''
    prices = []
    signals = []
    labels = []
    kwargs = None
    strategy = None
    def __init__(self, strategy):
        self.strategy = strategy
        return 
        
    def create_samples(self, prices, signals, labels, equipment_kwargs = {}):
        samples = list(zip(prices,signals))
        os.chdir('Petri Dishes')
        for i, label in enumerate(labels):
            sample = {'prices':samples[i][0],
                      'signal':samples[i][1], 
                      'kwargs':equipment_kwargs }
            
            with open(label+'.sample', 'wb') as f:
                pickle.dump(sample,f )
        os.chdir('..')

    
    def create_signal(self, data, bmask, smask):
        signal = pd.Series(index = data.index)
        signal[data.index] = 'hold'
        signal[bmask] = 'buy'
        signal[smask] = 'sell'
        return signal
    
    def get_data(self, name):
        data = pd.read_json(name)
        bmask, smask = self.strategy(data)       
        signal = self.create_signal(data, bmask, smask)
        return data, signal

    def get_all_data(self):
        names = glob.glob('Raw Data/*')
        prices = []
        signals = []
        for name in names:
            data, signal = self.get_data(name)
            prices.append(data['close'])
            signals.append(signal)
        
        labels =[]
        for label in names:
            labels.append(label.split('\\')[1].split('.')[0])
            
        return prices, signals, labels
    
    
    
    
def strategy(data):
    data['low_mean'] = data['low'].rolling(50).mean()
    data['high_mean'] = data['high'].rolling(50).mean()
    bmask = data['close'] < data['low_mean']
    smask = data['close'] > data['high_mean']
    return bmask, smask


  
def hire_scientist():
    time.sleep(0.1)
    nerd = Popen('python scientist.py', stdout=PIPE, stderr=PIPE)
    return nerd

def scientist_deligate(max_scientists = False):
    if max_scientists == False:
        max_scientists = multi.cpu_count()
    print('__ max nerds __', max_scientists)
    jobs_to_do = len(glob.glob('Petri Dishes\*.sample'))
    print('__ work to do__', jobs_to_do)
    
    done = False
    all_nerds = []
    while not done:
        files = glob.glob('Petri Dishes\*')
        if len(files) == 0:
            done = True
            
        working_nerds = 0
        for nerd in all_nerds:
            poll = nerd.poll()
            if poll is None:
                working_nerds = working_nerds + 1
            if poll is not None:
                words, complaint = nerd.communicate()
                if len(complaint) > 0:
                    raise Exception(complaint)
        if (working_nerds < max_scientists) and len(all_nerds) < jobs_to_do:
            all_nerds.append(hire_scientist())



#i = Intern(strategy)
#prices, signals, labels = i.get_all_data()

import time

i.create_samples(prices, signals, labels)

start = time.time()
scientist_deligate(8)
print(time.time()-start)