import glob
from subprocess import Popen, PIPE
import multiprocessing as multi
from analyst import Analyst
from intern import Intern
from abathor import Abathor
import numpy as np
import pandas as pd



def hire_scientist():
    global name
    name = name + 1
    nerd = Popen('python scientist.py {}'.format(name), stdout=PIPE, stderr=PIPE)
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



def study_strategies(presets):
    analyst = Analyst()
    for preset in presets.index:
        intern = Intern(strategy, preset)
        prices, signals, labels = intern.get_all_data()
        intern.create_samples(prices, signals, labels)
        scientist_deligate(8)
        analyst.get_parcel()
    return analyst.get_parcel()







    
