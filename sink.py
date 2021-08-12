import time

class Sink():
    def __init__(self,name,config):
        self.name=name
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
        self.nexttick=time.time()
    def nextinterval(self):
        # calculate next tick and skip if it is already in the past
        while self.nexttick<time.time():
            self.nexttick=self.nexttick+self.interval
    def update(self):
        pass
    def activate(self):
        pass
    def deactivate(self):
        pass
    def __str__(self):
        state="not_ready" if not self.is_ready else "active" if self.is_active else "ready"
        return str({"state":state})+"\n"
    def __repr__(self):
        return self.__str__()