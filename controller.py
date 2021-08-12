from source import Source
from source_e3dc import Source_e3dc
from sink import Sink
from charger import Charger
import logging

logger = logging.getLogger('controller')
logger.setLevel(logging.INFO)

import datetime

def dbgmsg(text):
    now=datetime.datetime.now()
    f=open('/home/pi/pichaco/ramdisk/error.log','a')
    f.write(now.strftime("%Y-%m-%d %H:%M:%S: ")+text+"\n")
    f.close()


class Controller():
    def __init__(self,name,config):
        dbgmsg("Starting")
        self.name=name
        self.object_list=[]
        for classname in ["sources","sinks"]:
            classcollection={}
            for object_name,object_config in config[classname].items():
                logger.info("creating object "+object_name+" from class "+str(object_config["class"]))
                new_object=globals()[object_config["class"]](object_name,object_config)
                classcollection[object_name]=new_object
                self.object_list.append(new_object)
            setattr(self,classname,classcollection)
    def do_control(self,tick):
        # determine overall reserve
        reserve=0
        capacity=0
        for power_source in self.sources.values():
            if tick%power_source.interval==0:
                try:
                    power_source.update()
                except:
                    logger.error(power_source.name+" did not answer as expected")
                    dbgmsg(power_source.name+" did not answer as expected")
                    # set reserve to zero to prevent overshoot if last valid value was high enough to encourage the sinks to increase consumption
                    power_source.reserve=0
            reserve+=power_source.reserve
            capacity+=power_source.capacity
        # notify sinks about reserve
        for power_sink in self.sinks.values():
            if tick%power_sink.interval==0:
                power_sink.reserve=reserve
                power_sink.capacity=capacity
                try:
                    power_sink.update()
                except:
                    logger.error(power_sink.name+ " did not answer as expected")
                    dbgmsg(power_sink.name+ " did not answer as expected")
    def __str__(self):
        return "sources: "+str(self.sources)+"\nsinks: "+str(self.sinks)
    def __repr__(self):
        return self.__str__()
