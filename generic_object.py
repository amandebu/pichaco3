import time
import os
import platform

class Generic_object():
    def __init__(self,name,config):
        self.name=name
        self.address=None
        self.__online=False
        self.callback_online=None
        self.callback_offline=None
        self.interval=int(config.get("interval","1"))
        self.nexttick=time.time()
        self.chokeing=False
        self.starving=False
    def get_online(self):
        return self.__online
    def set_online(self,state):
        if state!=self.__online:
            self.__online=state
            if state:
                if not self.callback_online is None:
                    self.callback_online()
            else:
                if not self.callback_offline is None:
                    self.callback_offline()
    online=property(get_online,set_online)
    def nextinterval(self):
        # calculate next tick and skip if it is already in the past
        while self.nexttick<time.time():
            self.nexttick=self.nexttick+self.interval
    def ping(self):
        if self.address is None:
            self.__online=True
            return True
        else:
            parameter="-n" if platform.system().lower()=="windows" else "-c"
            address=self.address
            self.online=os.system(f"ping {parameter} 1 -w2 {address} > /dev/null 2>&1")==0
            return self.online
    def update(self):
        pass
    def __str__(self):
        return self.name+"\n"
    def __repr__(self):
        return self.__str__()
