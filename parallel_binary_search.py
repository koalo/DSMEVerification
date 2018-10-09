# Performs parallel binary search

import time
import os
import random
from subprocess import *
from multiprocessing import *
from multiprocessing.managers import BaseManager
from threading import Timer

class Result(object):
    too_large = 0
    unknown = 1
    too_small = 2

class Task(object):
    def __init__(self,search,value):
        self.p = None
        self.search = search
        self.value = value
        self.terminated = False
        self.pid = 0

    def check(self):
        range = self.search.get_range()
        if self.p != None and not self.terminated:
            if not range[0] < self.value < range[1]:
                print "Terminate %s %d %i"%(self.cmd,self.value,self.pid)
                try:
                    self.p.terminate()
                except OSError:
                    pass # was already terminated in the meantime
            else:
                Timer(1, self.check, ()).start()

    def run(self):
        if self.terminated:
            return None
        
        self.p = Popen(self.cmd, stdout=PIPE, bufsize=-1)
        self.pid = self.p.pid

        self.check()

        with self.p.stdout:
            self.output = self.p.stdout.read()
        ru = os.wait4(self.p.pid, 0)[2]
        self.terminated = True
        elapsed = ru.ru_utime
    
        return (elapsed,self.cmd,self.process_result())

# Just a demo task
class Sleepy(Task):
    def __init__(self,search,value,unknown_range,additional_params):
        super(Sleepy,self).__init__(search,value)
        self.value = value

    def __enter__(self):
        self.cmd = ['sleep',str(random.randint(1,5))]
        return self

    def process_result(self):
        print "Exit %f"%self.value
        if self.value > 17:
            return Result.too_large
        elif self.value < 15:
            return Result.too_small
        else:
            return Result.unknown

    def __exit__(self,type,value,traceback):
        pass

class FoundException(Exception):
    pass

class Search(object):
    def __init__(self):
        self.processes = {}
        self.lock = Lock()

    def set_parameters(self,lower,upper,eps):
        self.lower = lower
        self.upper = upper
        self.unknown_lower = None
        self.unknown_upper = None
        self.eps = eps

    def optimal_next_value(self):
        self.lock.acquire() 
        if abs(self.upper-self.lower) < self.eps:
            self.lock.release()
            raise FoundException()
        values = [self.lower]
        values += filter(lambda x: self.lower < x and x < self.upper, sorted(self.processes.keys()))
        values += [self.upper]
        dist = [j-i for i, j in zip(values[:-1], values[1:])]
        max_dist = max(dist)
        max_dist_indices = [idx for idx, e in enumerate(dist) if e == max_dist]
        max_dist_centers = [(values[idx]+values[idx+1])/2.0 for idx in max_dist_indices]
        center = (self.upper+self.lower)/2
        value = min(max_dist_centers, key = lambda x:abs(x-center))
        print "Next value %f"%value
        self.processes[value] = None
        self.lock.release()
        return value

    def add_process(self,value,process):
        assert self.processes.has_key(value) and self.processes[value] == None
        #print value
        self.processes[value] = process

    def run_process(self,value):
        return self.processes[value].run()

    def remove_process(self,value):
        self.lock.acquire() 
        del self.processes[value]
        self.lock.release() 

    def unknown_range(self):
        return (self.unknown_lower,self.unknown_upper)

    def get_range(self):
        return (self.lower,self.upper)

    def handle_result(self,value,result):
        self.lock.acquire() 
        # calculate new boundaries
        # min and max since another process could have been finished first
        if result == Result.too_large:
            self.upper = min(value,self.upper)
        elif result == Result.too_small:
            self.lower = max(value,self.lower)
        else: # unknown
            # unknown grows while upper/lower shrinks
            if self.unknown_lower == None or self.unknown_lower > value:
                self.unknown_lower = value
            if self.unknown_upper == None or self.unknown_upper < value:
                self.unknown_upper = value
            
        # unknown can never be larger than upper/lower
        if self.unknown_lower != None:
            self.unknown_lower = max(self.unknown_lower,self.lower)
        if self.unknown_upper != None:
            self.unknown_upper = min(self.unknown_upper,self.upper)

        print str(self.lower)+" - "+str(self.unknown_lower)+" - "+str(self.unknown_upper)+" - "+str(self.upper)

        self.lock.release() 
        

class SearchManager(BaseManager):
    pass

SearchManager.register('Search',Search)

def job(value,search,task_class,additional_params):
    unknown_range = (search.unknown_range()[0] <= value <= search.unknown_range()[1])
    with task_class(search,value,unknown_range,additional_params) as s:
        search.add_process(value,s)
        elapsed, cmd, result = search.run_process(value)
        search.remove_process(value)

    search.handle_result(value,result)
    return search

def finished(result):
    result.release()

class ParallelBinarySearch(object):
    def __init__(self,task_class,lower,upper,eps,additional_params = ''):
        self.task_class = task_class
        self.manager = SearchManager()
        self.manager.start()
        self.search = self.manager.Search()
        self.search.set_parameters(lower,upper,eps)
        self.additional_params = additional_params

    def run_next(self,pool,callback):
        try:
            value = self.search.optimal_next_value()
        except FoundException:
            return False

        pool.apply_async(job,args=[value,self.search,self.task_class,self.additional_params],callback=callback)
        return True

    def final(self):
        result = self.search.get_range()
        print "Result ",
        print result
        return result
