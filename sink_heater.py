from enum import IntEnum
import requests
import time
import json
import logging
import os
logger = logging.getLogger('sink_heater')
logger.setLevel(logging.INFO)
from sink import Sink

class Sink_heater(Sink):
    def __init__(self,name,config):
        super().__init__(name,config)
        self.address=config.get("address")
        self.config=config

    def update(self):
        if self.nexttick<time.time():
            self.nextinterval()
#            if self.plug_state!=Plug_states.INITIALIZE_CHARGER:
            data=self.http_get("status")
            if not data is None:
                self.data=data
                self.read_data()
                self.statemachine()
            print(self.name+": "+str(self),end="")

    def http_get(uri):    
        print("trying to get data from", self.address)
        try:
            r = requests.get("http://"+str(self.address)+"/"+uri)
            self.reachable=True
        except:
            self.reachable=False
        if self.reachable:
            if r.status_code==200:
                data=r.text
                try:
                    data=r.json()
                except:
                    pass
                return data
            else:
                return None


    def __str__(self):
        return str({
            "reserve":self.reserve,
            "chokeing":self.chokeing
        })+"\n"
