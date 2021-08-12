from generic_object import Generic_object

class Source(Generic_object):
    def __init__(self,name,config):
        super().__init__(name,config)
        self.reserve=config["reserve"]
        self.capacity=config["capacity"]
