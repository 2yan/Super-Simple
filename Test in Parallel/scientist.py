import os
import glob
import pickle
from rack import Equipment
import pandas as pd

logfile = 'journal.txt'

def log(message):
    print(message)
    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    with open(logfile, "a") as f:
        f.write(message)
    return


def get_files_by_size():
    unordered = glob.glob('*.sample')
    data = pd.DataFrame(index = unordered)
    data['sizes'] = data.index.map(os.path.getsize)
    data = list(data.sort_values('sizes', ascending = False).index)
    return data

class Scientist():
    current_work = None
    
    def __init__(self):
        return
    
    
    
    def reserve_work(self):
        done = False
        while not done:
            try:
                dishes = get_files_by_size()
                if len(dishes) == 0:
                    raise Exception("Ain't got no work to do")
                sample_dish = dishes[0]
                dish = sample_dish.split('.')[0] + '.processing'
                os.rename(sample_dish,dish )
                done = True
            except FileNotFoundError:
                pass
        return dish
    
    def get_sample(self):
        os.chdir('Petri Dishes')
        dish = self.reserve_work()
        self.current_work = dish.split('.')[0]
        with open(dish, 'rb') as f:
            dish = pickle.load(f)
        os.chdir('..')
        return dish
        
    def do_research(self, sample):
        equipment = Equipment(**sample['kwargs'])
        result = equipment.test_signal(sample['prices'], sample['signal'])
        os.chdir('Publications')
        with open(self.current_work+'.result', 'wb') as f:
            pickle.dump(result, f)
        os.chdir('..')
    
    def clean_dishes(self):
        os.chdir('Petri Dishes')
        os.remove(self.current_work + '.processing')
        os.chdir('..')
    
if __name__ == '__main__':
    john = Scientist()
    sample = john.get_sample()
    john.do_research(sample)
    john.clean_dishes()

    
    