class Source():
    def __init__(self,name,config):
        self.name=name
        self.reserve=config["reserve"]
        self.capacity=config["capacity"]
        self.interval=int(config.get("interval","1"))
    def update(self):
        pass
    def __str__(self):
        return str({"reserve":self.reserve,"capacity":self.capacity})+"\n"
    def __repr__(self):
        return self.__str__()