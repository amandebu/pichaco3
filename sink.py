import time
from generic_object import Generic_object

class Sink(Generic_object):
    def __init__(self,name,config):
        super().__init__(name,config)
        self.is_active=False
        self.is_ready=False
        self.min_activation_power=0
        self.current_power=0
        self.power_step=0
        self.priority=0
        self.min_power=0
        self.reserve=0
        self.capacity=0
        self.interval=int(config.get("interval","5"))
    def activate(self):
        pass
    def deactivate(self):
        pass
    def __str__(self):
        state="not_ready" if not self.is_ready else "active" if self.is_active else "ready"
        return str({"state":state})+"\n"
