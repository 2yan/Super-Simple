import pandas as pd


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