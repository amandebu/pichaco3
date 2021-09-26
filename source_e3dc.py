from pymodbus.client.sync import ModbusTcpClient
from source import Source

class Source_e3dc(Source):
    def __init__(self,name,config):
        super().__init__(name,config)
        self.port=int(config.get("port","502"))
        self.address=config.get("address")
        self.data={}
    def update(self):
        if not self.address is None:
            data=getData(address=self.address,port=self.port)
            data["alienPower"]=-data["powermeter_1_l1"]-data["powermeter_1_l2"]-data["powermeter_1_l3"]
            self.reserve=max(data["pvPower"],0)-max(data["housePower"],0)-min(data["powermeter_1_l1"],0)-min(data["powermeter_1_l2"],0)-min(data["powermeter_1_l3"],0)
            # self.reserve=max(data["pvPower"],0)-max(data["housePower"],0)-min(data["powermeter_1_l1"],0)-min(data["powermeter_1_l2"],0)-min(data["powermeter_1_l3"],0)-max(data["batteryPower"],0)
            data["reserve"]=self.reserve
            if self.chokeing<=95 and self.chokeing:
                self.chokeing=False
            elif self.chokeing>=99 and not self.chokeing:
                self.chokeing=True
            data["chokeing"]=self.chokeing
            self.data=data
        print(self.name+": "+str(self))
    def __str__(self):
        result={}
        for key in ["pvPower","batteryPower","housePower","gridPower","soc","alienPower","reserve","chokeing"]: 
            result[key]=self.data[key]
        return str(result)

class ModbusConnection(ModbusTcpClient):
    def __init__(self,address,port,offset):
        super().__init__(address, port)
        self.connect()
        # client specific offset of range
        self.__offset = offset

    def hi(self,value):
        return value >> 8

    def lo(self,value):
        return value & 0xFF

    def read_register_uint16(self,reg):
        try:
            resp = self.read_holding_registers(reg+self.__offset,1,unit=1)
            return resp.registers[0]
        except:
            return None

    def read_register_int16(self,reg):
        try:
            value1 = self.read_register_uint16(reg)
            if value1>32767:
                value1+=-65536
            return value1
        except:
            return None

    def read_register_uint32(self,reg):
        try:
            resp = self.read_holding_registers(reg+self.__offset,2,unit=1)
            return resp.registers[1]*65536+resp.registers[0]
        except:
            return None

    def read_register_int32(self,reg):
        try:
            value1 = self.read_register_uint32(reg)
            if value1>2147483647:
                value1+=-4294967296
            return value1
        except:
            return None

    def read_register_str(self,reg,count):
        try:
            resp = self.read_holding_registers(reg+self.__offset,count,unit=1)
            result=""
            for i in range(0,count-1):
                hi=self.hi(resp.registers[i])
                lo=self.lo(resp.registers[i])
                result+=("" if hi==0 else chr(hi))+("" if lo==0 else chr(lo))
            return result
        except:
            return None

def getData(address,port):
    powermetertypes="not installed,root,external production,bidirectional,external consumption,farm,not in use,wallbox,external farm,viewonly,control bypass".split(",")
    result={}
    try:
        mb=ModbusConnection(address,port,-1)
        if mb.read_register_uint16(40001)==58332:
            reg=mb.read_register_uint16(40002)
            result["modbusFirmware"]=str(mb.hi(reg))+"."+str(mb.lo(reg))
            result["registerCount"]=mb.read_register_uint16(40003)
            result["manufacturer"]=mb.read_register_str(40004,16)

            result["model"]=mb.read_register_str(40020,16)
            result["serial"]=mb.read_register_str(40036,16)
            result["firmware"]=mb.read_register_str(40052,16)

            result["pvPower"]=mb.read_register_int32(40068)
            result["batteryPower"]=mb.read_register_int32(40070)

            result["housePower"]=mb.read_register_int32(40072)
            result["gridPower"]=mb.read_register_int32(40074)
            
            result["generatorPower"]=mb.read_register_int32(40076)
            result["wallboxPower"]=mb.read_register_int32(40078)
            
            result["wallboxPVPower"]=mb.read_register_int32(40080)
            reg=mb.read_register_uint16(40082)
            result["autarky"]=mb.hi(reg)
            result["selfconsumption"]=mb.lo(reg)

            result["soc"]=mb.read_register_uint16(40083)
            result["islandMode"]=mb.read_register_uint16(40084)==1
    #        result["emsStatus"]=mb.read_register_uint16(40085)
            if result["registerCount"]>103:
                s1=mb.read_register_uint16(40102)
                s2=mb.read_register_uint16(40103)
                result["DCPower_string1"]=s1
                result["DCPower_string2"]=s2
                result["DCPower_sum"]=s1+s2
            powerMeters=[]
            if result["registerCount"]>127:
                for powerMeterIndex in range(7):
#                for powerMeterIndex in [0,1,2,3,4,5,6]:
                    reg=40105+powerMeterIndex*4
                    result["powermeter_"+str(powerMeterIndex)+"_type"]=powermetertypes[mb.read_register_uint16(reg)]
                    result["powermeter_"+str(powerMeterIndex)+"_l1"]=mb.read_register_int16(reg+1)
                    result["powermeter_"+str(powerMeterIndex)+"_l2"]=mb.read_register_int16(reg+2)
                    result["powermeter_"+str(powerMeterIndex)+"_l3"]=mb.read_register_int16(reg+3)
        else:
            result["error"]="E3/DC not found at Modbus address 40001 of device "+address
    except:
        result["error"]="Error accessing E3/DC at Modbus address 40001 of device "+address
    return result


