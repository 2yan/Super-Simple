import pandas as pd
import glob
import pickle
import os
import sys

logfile = 'intern_journal.txt'

def log(message):
    from datetime import datetime
    with open(logfile, 'a') as f:
        f.write('\n')
        f.write(datetime.now().isoformat())
        f.write('    :')
        f.write(message)
    return 

def get_files_by_size():
    unordered = glob.glob('Raw Data\*.json')
    data = pd.DataFrame(index = unordered)
    data['sizes'] = data.index.map(os.path.getsize)
    data = list(data.sort_values('sizes', ascending = False).index)
    return data

class Intern():
    ''' The Strategy Argument is a function that works with a the dataframes found in raw_data.
    It Labels each position as hold, buy and sell '''
    prices = []
    signals = []
    labels = []
    kwargs = None
    strategy = None
    
    def __init__(self, strategy, position):
        self.strategy = strategy
        self.position = position
        return 
    
    
    def __rename_file(self, start, end):
        os.rename(start, end)
        while os.path.exists(start):
            continue
        done = False
        while not done:
            try:
                with open(end, 'rb') as f:
                    end = pickle.load(f)
                done = True
            except PermissionError:
                pass
        return end
    
    def reserve_work(self):
        done = False
        while not done:
            try:
                raw_data = get_files_by_size()
                if len(dishes) == 0:
                    raise Exception("Ain't got no work to do")
                sample_dish = dishes[0]
                dish = sample_dish.split('.')[0] +'x{}x.processing'.format(self.name)
                self.__rename_file(sample_dish,dish )
                
                if os.path.exists(dish):
                    done = True
                
            except (FileNotFoundError, PermissionError) as e:
                pass
            
        return dish
    
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
        bmask, smask = self.strategy(data, self.position)       
        signal = self.create_signal(data, bmask, smask)
        return data, signal

    def get_all_data(self):
        names = glob.glob('Raw Data/*')
        prices = []
        signals = []
        for name in names:
            print(name)
            data, signal = self.get_data(name)
            prices.append(data['close'])
            signals.append(signal)
        
        labels =[]
        for label in names:
            labels.append(label.split('\\')[1].split('.')[0])
            
        return prices, signals, labels
    
    

if __name__ == '__main__':
    from strategist import strategy
    try:
        which = sys.argv[1]
    except IndexError:
        which = 0
    sarah = Intern(strategy, which)
