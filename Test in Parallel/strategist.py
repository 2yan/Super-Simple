
from abathor import Abathor
import numpy as np
import pandas as pd


def __strategy__(cans, aba, signal_time, deviation, flip):
    bands = aba.get_bollinger(cans, signal_time, deviation)
    bmask = cans['close'].rolling(3).mean().bfill() < bands['lower']
    smask = cans['close'].rolling(3).mean().bfill() > bands['upper'] 
    
    if flip:
        bmask,smask = smask,bmask
    
    return bmask, smask
        
def strategy(data, i ):
    global aba
    signal_time = presets.loc[i, 'signal_time']
    deviation = presets.loc[i, 'deviation']
    flip = presets.loc[i, 'flip']
    return __strategy__(data, aba, signal_time, deviation, flip)



aba = Abathor('LTC-USD')

presets = pd.DataFrame()
times = 10
presets['signal_time'] = np.random.randint(1, 1000, times)
presets['deviation'] = np.random.randint(1, 5800, times)/1000
presets['max_loss'] = np.random.randint(0, 300, times)/1000
presets['target_percent'] = np.random.randint(0, 300, times)/1000
presets['flip'] = np.random.randint(0, 2, times, dtype='bool')