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
    msg=now.strftime("%Y-%m-%d %H:%M:%S: ")+text+"\n"
    f.write(msg)
    f.close()
    print("WROTE "+msg+" TO DISC")

def printonline(object):
    dbgmsg(object.name+" is "+("online" if object.online else "offline"))

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
                new_object.callback_online=lambda: printonline(new_object)
                new_object.callback_offline=lambda: printonline(new_object)
                classcollection[object_name]=new_object
                self.object_list.append(new_object)
            setattr(self,classname,classcollection)
    def do_control(self,tick):
        # determine overall reserve
        reserve=0
        capacity=0
        chokeing=False
        starving=False
        for power_source in self.sources.values():
            if tick%power_source.interval==0:
                if not power_source.online:
                    power_source.ping()
                if power_source.online:
                    try:
                       power_source.update()
                    except:
                       power_source.ping()
                       msg=power_source.name+" did not answer as expected, it is "+"online" if power_source.online else "offline"
                       logger.error(msg)
                       dbgmsg(msg)
                       # set reserve to zero to prevent overshoot if last valid value was high enough to encourage the sinks to increase consumption
                       power_source.reserve=0
                    reserve+=power_source.reserve
                    capacity+=power_source.capacity
                    chokeing=chokeing or power_source.chokeing
                    starving=starving or power_source.starving
                else:
                    logger.info(power_source.name+" is offline")
        # notify sinks about reserve
        for power_sink in self.sinks.values():
            if tick%power_sink.interval==0:
                if not power_sink.online:
                   power_sink.ping()
                if power_sink.online:
                    power_sink.reserve=reserve
                    power_sink.capacity=capacity
                    power_sink.chokeing=chokeing
                    power_sink.starving=starving
                    try:
                        power_sink.update()
                    except:
                        power_sink.ping()
                        msg=power_sink.name+ " did not answer as expected, it is "+"online" if power_sink.online else "offline"
                        logger.error(msg)
                        dbgmsg(msg)
                else:
                    logger.info(power_sink.name+" is offline")
    def __str__(self):
        return "sources: "+str(self.sources)+"\nsinks: "+str(self.sinks)
    def __repr__(self):
        return self.__str__()
