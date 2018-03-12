import os
import glob
import pickle
from rack import Equipment

import pandas as pd
import sys

logfile = 'scientist_journal.txt'

def log(message):
    from datetime import datetime
    with open(logfile, 'a') as f:
        f.write('\n')
        f.write(datetime.now().isoformat())
        f.write('    :')
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
    name = None
    def __init__(self, name):
        self.name = name
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
                dishes = get_files_by_size()
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
        equipment.test_signal(sample['prices'], sample['signal'])
        os.chdir('Publications')
        name = self.current_work.replace('x{}x'.format(self.name), '')
        with open(name +'.result', 'wb') as f:
            pickle.dump(equipment, f)
        os.chdir('..')
    
    def clean_dishes(self):
        os.chdir('Petri Dishes')
        os.remove(self.current_work + '.processing')
        os.chdir('..')
    
if __name__ == '__main__':
    name = sys.argv[1]
    john = Scientist(name)
    sample = john.get_sample()
    john.do_research(sample)
    john.clean_dishes()

    
    