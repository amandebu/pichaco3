import time
import os
import platform

class Generic_object():
    def __init__(self,name,config):
        self.name=name
        self.address=None
        self.interval=int(config.get("interval","1"))
        self.nexttick=time.time()
    def nextinterval(self):
        # calculate next tick and skip if it is already in the past
        while self.nexttick<time.time():
            self.nexttick=self.nexttick+self.interval
    def ping(self):
        if self.address is None:
            return True
        else:
            parameter="-n" if platform.system().lower()=="windows" else "-c"
            address=self.address
            return os.system(f"ping {parameter} 1 -w2 {address} > /dev/null 2>&1")==0
    def update(self):
        pass
    def __str__(self):
        return self.name+"\n"
    def __repr__(self):
        return self.__str__()
