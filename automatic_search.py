#!/usr/bin/env python

from subprocess import *
import multiprocessing
import multiprocessing.pool
import os
import tempfile
import itertools
import time
import signal
import random
from parallel_binary_search import *
import re
import sys
import datetime
from pprint import *

verifyta = os.path.expanduser('~/Programs/uppaal-4.0.14/bin-Linux/verifyta')
original_model = 'DSMEVerification_withoutNodeFailures.xml' 

max_num_jobs = int(sys.argv[1])

class Verifier(Task):
    def __init__(self,search,value,unknown_range,additional_params=''):
        super(Verifier,self).__init__(search,value)
        self.value = value
        self.query = additional_params['query']
        self.improved = additional_params['improved']
        self.macDSMEGTSExpirationTime = additional_params['macDSMEGTSExpirationTime']
        self.MO = additional_params['MO']
        if unknown_range:
            self.cmd_params = ''
        else:
            self.cmd_params = additional_params['cmd_params']

    def printPrefix(self):
        print "MO_%i_Exp_%i_Value_%i: "%(self.MO,self.macDSMEGTSExpirationTime,self.value) ,

    def __enter__(self):
        modelfd, self.model_path = tempfile.mkstemp(suffix='.xml')
        queryfd, self.query_path = tempfile.mkstemp()

        self.printPrefix()
        print "start"

        with os.fdopen(modelfd, 'w') as model:
            with open(original_model,'r') as original:
                for line in original:
                    if 'const int macDSMEGTSExpirationTime' in line:
                        model.write('const int macDSMEGTSExpirationTime = %i; // given in Multi-Superframes\n'%(self.macDSMEGTSExpirationTime))
                    elif 'const int MO' in line:
                        model.write('const int MO = %i;'%self.MO)
                    elif 'const int T_MAXINCONS' in line:
                        model.write("const int T_MAXINCONS = %d;\n"%(self.value))
                    elif 'const bool improved' in line:
                        if self.improved:
                            model.write("const bool improved = true;")
                        else:
                            model.write("const bool improved = false;")
                    else:
                        model.write(line)

        with os.fdopen(queryfd, 'w') as queryf:
            queryf.write(self.query)

        self.cmd = ['time',verifyta]
        self.cmd += filter(None,self.cmd_params)
        self.cmd += [self.model_path,self.query_path]
        
        return self

    def process_result(self):
        self.printPrefix()
        if " -- Property is satisfied." in self.output:
            print "satisfied"
            return Result.too_large
        elif " -- Property is MAYBE satisfied." in self.output:
            print "MAYBE satisfied"
            return Result.unknown
        elif " -- Property is NOT satisfied." in self.output:
            print "NOT Satisfied"
            return Result.too_small
        else:
            assert False

    def __exit__(self,type,value,traceback):
        #print "Remove files"
        os.remove(self.model_path)
        os.remove(self.query_path)
    
variants = [
    ['-q'],
    ['-s'],
    ['','-A'],
    ['','-C'],
]

class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

class MyPool(multiprocessing.pool.Pool):
    Process = NoDaemonProcess

def find_fastest_params():
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = Pool(max_jobs)
    signal.signal(signal.SIGINT, original_sigint_handler)

    print pool.map(verify,itertools.product(*variants))

def init_search(params):
    symbols_per_hour = 2.25 * 1e8 # in symbols
    SO = 3
    aBaseSlotDuration = 60
    symbols_per_superframe = 16 * aBaseSlotDuration * (1 << SO)
    superframes_per_hour = symbols_per_hour / symbols_per_superframe
    print superframes_per_hour
    max_value = superframes_per_hour*6
    min_value = 0
    return ParallelBinarySearch(Verifier,min_value,max_value,1,params)

def single_run():
    now = datetime.datetime.now()
    params = {
      'MO': 4,
      'macDSMEGTSExpirationTime': 7,
      'improved': True,
      'query': 'A[] observer.inconsistentFor < T_MAXINCONS\n',
      'cmd_params': []
    }

    with Verifier(10,False,params) as v:
        print v.cmd
        call(v.cmd)

def iterateVars():
    param_list = []

    for MO in [12,13,14,15,16]:
        for macDSMEGTSExpirationTime in [5,7,9]:
            for improved in [True,False]:
                param_list.append({
                  'jobs': 1,
                  'MO': MO,
                  'macDSMEGTSExpirationTime': macDSMEGTSExpirationTime,
                  'improved': improved,
                  'query': 'A[] observer.inconsistentFor < T_MAXINCONS\n',
                  'cmd_params': []
                })

    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = MyPool(max_num_jobs)
    signal.signal(signal.SIGINT, original_sigint_handler)

    for i in range(0,len(param_list)):
        param_list[i]['jobs'] = max(1,int(max_num_jobs/len(param_list)))
        print param_list[i]['jobs']

    results = {}
    event = Event()
    searches = {}
    prlist = dict(zip(range(0,len(param_list)), param_list))

    def callback_closure(i):
        def callback(result):
            cont = searches[i].run_next(pool,callback_closure(i))
            if not cont:
                results[i] = searches[i].final()

                print "Finished %i"%i
                prlist[i]['result'] = results[i]
                pprint(prlist)

                if len(results.keys()) == len(param_list):
                    event.set()
        return callback
         
    for i in range(0,len(param_list)):
        searches[i] = init_search(param_list[i])

        for j in range(0,param_list[i]['jobs']):
            cl = callback_closure(i)
            cl(None)
    
    event.wait()
    print "Closing"

    for i in range(0,len(param_list)):
        print param_list[i] 
        print results[i]
    
    pool.close()
    pool.join()

#single_run()
#find_optimum(jobs = 3, MO = 5, macDSMEGTSExpirationTime = 7)
iterateVars()
#search(Sleepy,max_num_jobs,0,100,0.5)
