from enum import IntEnum
import requests
import time
import json
import logging
import os
logger = logging.getLogger('charger')
logger.setLevel(logging.INFO)
from sink import Sink

data_override_file="debug_data.json"

MIN_AMP=6
TIMEOUT_DETECT_VEHICLE = 60
TIMEOUT_WAIT_FOR_PLUG_IN = 12
UPHYSTERESIS = 20
DOWNHYSTERESIS = -20
FINISHEDLIMIT = 100
SWITCHPHASEHYSTERESIS = 300
DEFAULTPHASESWITCHSTEP = 2100000 # just a high number

class Plug_states(IntEnum):
    INITIALIZE_CHARGER = 0
    RESTARTING = 1
    WAITING_FOR_VEHICLE_PLUGGING_IN = 2
    PLUGGED_IN = 3

plug_states=[
    "initialize charger",
    "restarting",
    "waiting for vehicle plugging in",
    "plugged in"
]

class Charge_states(IntEnum):
    UNPLUGGED = 0
    INITIALIZE_VEHICLE = 1
    WAITING_FOR_INITIALIZED_VEHICLE = 2
    CHARGING = 3
    WAITING_FOR_POWER = 4
    FINISHED = 5

charge_states=[
    "unplugged",
    "initialize vehicle",
    "waiting for initialized vehilce",
    "charging",
    "wait for power",
    "finished"
]

class Charger_modes(IntEnum):
    AUTOMATIC = 0 # use self generated power only
    MANUAL = 1 # use at least the amps given by button or app
    AMOUNT = 2 # charge manually given amount of energy and then switch back to automatic
    MARKET = 3 # reserved for later

charger_modes=[
    "automatic",
    "manual",
    "amount",
    "market"
]

class Charger(Sink):
    def __init__(self,name,config):
        super().__init__(name,config)
        self.address=config.get("address")
        self.config=config
        self._charge_state=None
        self._plug_state=None
        self.charge_state=Charge_states.UNPLUGGED
        self.plug_state=Plug_states.INITIALIZE_CHARGER
        self.min_amp=int(config.get("min_amp","6"))
        self.max_amp=int(config.get("max_amp","16"))
        self.amp=-1
        self.override_amp=0
        self._car_phase_count=0
        self._used_phase_count=0
        self.is_pluggedin=False
        self.connected_phase_count=0
        self.voltage=0
        self.charging_power=0
        self.step_power=0
        self.start_power=0
        self.switch_phase_power=DEFAULTPHASESWITCHSTEP
        self.charger_activated=False
        self.phases_set=-1
        #default for start and step power are 230V 3 phases
#        self.voltage=230
#        self.car_phase_count=3
        self.wait_for_kw_stop=False
        self.wait_for_car_timeout=0
        self.statemachine()

    def get_car_phase_count(self):
        return self._car_phase_count
    def set_car_phase_count(self,phases):
        self._car_phase_count=phases
        self.used_phase_count=phases
    car_phase_count=property(get_car_phase_count,set_car_phase_count)

    def get_used_phase_count(self):
        return self._used_phase_count
    def set_used_phase_count(self,phases):
        self._used_phase_count=min(phases,self._car_phase_count)
        self.step_power=int(self._used_phase_count*self.voltage)
        self.start_power=self.min_amp*self.step_power
    used_phase_count=property(get_used_phase_count,set_used_phase_count)


    def update_charge_mode(self,oldmode):
        newmode=self.get_charge_mode()
        if newmode!=oldmode:
            logger.info(self.name+" switched charger mode to "+charger_modes[newmode])

    def get_charge_mode(self):
        if self.wait_for_kw_stop:
            return Charger_modes.AMOUNT
        elif self.override_amp>0:
            return Charger_modes.MANUAL
        else:
            return Charger_modes.AUTOMATIC
    charge_mode=property(get_charge_mode)

    def get_plug_state(self):
        return self._plug_state
    def set_plug_state(self,state):
        if self._plug_state!=state:
            self._plug_state=state
            logger.info(self.name+" Switching to plug state "+plug_states[state])
    plug_state=property(get_plug_state,set_plug_state)

    def get_charge_state(self):
        return self._charge_state
    def set_charge_state(self,state):
        if self._charge_state!=state:
            if state==Charge_states.CHARGING:
                pass
            self._charge_state=state
            logger.info(self.name+" Switching to charge state "+charge_states[state])
    charge_state=property(get_charge_state,set_charge_state)

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

    def set_amp(self,newvalue):
        if newvalue<self.min_amp:
            newvalue=self.min_amp
        if newvalue<self.override_amp:
            newvalue=self.override_amp
        if newvalue>self.max_amp:
            newvalue=self.max_amp
        if newvalue!=self.amp:
            cmd="amx" if self.capabilities["amx"] else "amp"
            # update self.amp before a call of read_data to
            # prevent interpretation as override amp
            self.amp=newvalue
            self.data=self.http_get("mqtt?payload="+cmd+"="+str(newvalue))

    def switch_phases(self,phase_count):
        if phase_count>1:
            if self.phases_set!=3:
                data=self.http_get("api/set?psm=2")
                self.phases_set=3
                self.used_phase_count=3
                logger.info(self.name+" switched used phases to "+str(self.used_phase_count))
        else:
            if self.phases_set!=1:
                data=self.http_get("api/set?psm=1")
                self.phases_set=1
                self.used_phase_count=1
                logger.info(self.name+" switched used phases to "+str(self.used_phase_count))

    def activate_charger(self,run):
        alw=int(self.data["alw"])
        if run!=(alw==1):
            self.data=self.http_get("mqtt?payload=alw="+str(1 if run else 0))

    def http_get(self,uri):
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

    def read_data(self):
        if data_override_file!="":
            try:
                with open(os.path.dirname(os.path.abspath(__file__))+data_override_file) as json_file:
                    override_data = json.load(json_file)
                    res=override_data.get("res")
                    if not res is None:
                        self.reserve=int(res)
            except:
                override_data={}
            self.data={**self.data,**override_data}
        self.is_pluggedin=self.data["car"] in [2,3,4]
        self.connected_phase_count=0
        self.voltage=0
        for phase_number in range(3):
            if self.data["nrg"][phase_number]:
                self.voltage+=self.data["nrg"][phase_number]*self.correction_factor
                self.connected_phase_count+=1
        self.voltage=int(self.voltage//self.connected_phase_count)
        self.current_power=int(round(self.data["nrg"][11]*self.correction_factor*10,0))
        oldmode=self.get_charge_mode()
        if int(self.data["amp"])!=self.amp:
            # amp value was set outside via device button or app and will be used as
            # override value
            self.override_amp=int(self.data["amp"])
            self.wait_for_car_timeout=time.time()+TIMEOUT_WAIT_FOR_PLUG_IN
        # if amount to charge is set via app temporaryly set override_amp to
        # make sure the amount is charged before going back to automatic
        if int(self.data["dwo"])>0 and not self.wait_for_kw_stop:
            self.wait_for_kw_stop=True
            if self.override_amp==0:
                self.override_amp=int(self.data["amp"])
                if int(self.data["car"])==1:
                    # wait 2 minutes for plugin of a car before returning to automatic mode
                    self.wait_for_car_timeout=time.time()+TIMEOUT_WAIT_FOR_PLUG_IN
        if self.wait_for_kw_stop and int(self.data["dwo"])==0:
            self.wait_for_kw_stop=False
            self.override_amp=0
        self.amp=int(self.data["amp"])
        self.car=int(self.data["car"])
        self.charger_activated=int(self.data["alw"])==1
        self.charging_power=int(int(self.data["nrg"][11]*10*self.correction_factor))
        self.update_charge_mode(oldmode)

    def statemachine(self):
        if self.plug_state==Plug_states.INITIALIZE_CHARGER:
            self.reachable=False
            # older chargers tend to measure a too low volate
            # as power is measured voltage*current, power needs same correction
            self.correction_factor=1.05 
            self.capabilities={"phaseswitch":False,"amx":False}
            if not self.address is None:
                data=self.http_get("api/status")
                if not data is None:
                    self.capabilities["phaseswitch"]=True
                    #HW3 ist more correct than deviation of 5% from HW2 and bef6ore
                    self.correction_factor=1
                self.correction_factor=float(self.config.get("correction_factor",str(self.correction_factor)))
                self.data=self.http_get("status")
                if not self.data is None:
                    if float(self.data["fwv"])>=40:
                        self.capabilities["amx"]=True
                    self.read_data()
                    self.set_amp(0)
                if self.reachable:
                    self.plug_state=Plug_states.RESTARTING
        if self.plug_state==Plug_states.RESTARTING:
            oldmode=self.get_charge_mode()
            # reset charger mode to automatic
            self.charger_mode=Charger_modes.AUTOMATIC
            self.switch_phase_power=DEFAULTPHASESWITCHSTEP
            # set phases to 3
            if self.connected_phase_count>1 and self.capabilities["phaseswitch"]:
                self.switch_phases(3)
            # reset override_amp if restarting
            self.override_amp=0
            self.wait_for_car_timeout=0
            # set amp to minimum to notice when it was changed
            self.set_amp(MIN_AMP)
            # activate pwm signal to make button work
            self.activate_charger(True)
            # find next state
            self.update_charge_mode(oldmode)
            if self.car==1:
                self.plug_state=Plug_states.WAITING_FOR_VEHICLE_PLUGGING_IN
                self.charge_state=Charge_states.UNPLUGGED
            else:
                self.plug_state=Plug_states.PLUGGED_IN
                self.charge_state=Charge_states.INITIALIZE_VEHICLE
        if self.plug_state==Plug_states.WAITING_FOR_VEHICLE_PLUGGING_IN:
            if self.car!=1:
                self.plug_state=Plug_states.PLUGGED_IN
                self.charge_state=Charge_states.INITIALIZE_VEHICLE
            else:
                if time.time()>self.wait_for_car_timeout:
                    oldmode=self.get_charge_mode()
                    self.override_amp=0
                    self.update_charge_mode(oldmode)
                    self.set_amp(MIN_AMP)
        if self.plug_state==Plug_states.PLUGGED_IN:
            if self.car==1:
                self.plug_state=Plug_states.RESTARTING
            elif self.charge_state==Charge_states.INITIALIZE_VEHICLE:
                #detect vehicle
                if self.connected_phase_count==1:
                    self.car_phase_count=1
                    self.charge_state=Charge_states.CHARGING
                else:
                    self.timeout=time.time()+TIMEOUT_DETECT_VEHICLE # wait 15 seconds to detect number of phases that the car uses
                    self.charge_state=Charge_states.WAITING_FOR_INITIALIZED_VEHICLE
            elif self.charge_state==Charge_states.WAITING_FOR_INITIALIZED_VEHICLE:
                if self.current_power<FINISHEDLIMIT:
                    # reset the timeout as long the vehicle does not draw power,
                    # e.g. because it is fully charged or in sleep mode
                    self.timeout=time.time()+TIMEOUT_DETECT_VEHICLE
                car_phase_count=0
                for index in [7,8,9]:
                    if self.data["nrg"][index]>0:
                        car_phase_count+=1
                # if all three phases are used or timeout is over proceed with charging
                if (car_phase_count>2) or ((time.time()>self.timeout) and (car_phase_count>0)):
                    self.timeout=0
                    self.car_phase_count=car_phase_count
                    self.used_phase_count=car_phase_count
                    self.switch_phase_power=self.start_power+SWITCHPHASEHYSTERESIS
                    self.charge_state=Charge_states.CHARGING
            if self.charge_state==Charge_states.CHARGING:
                if self.reserve<DOWNHYSTERESIS:
                    newamp=max(self.override_amp,self.amp)-1
                    self.set_amp(newamp)
                    if newamp<self.min_amp:
                        # not enough power available
                        # step 1: switch to single phase if possible
                        if self.used_phase_count>1 and self.capabilities["phaseswitch"]:
                            if self.reserve<-SWITCHPHASEHYSTERESIS:
                                self.switch_phases(1)
                        else:
                        # otherwise deactivate charger
                            self.activate_charger(False)
                            self.charge_state=Charge_states.WAITING_FOR_POWER
                    if self.current_power<FINISHEDLIMIT:
                        self.charge_state=Charge_states.FINISHED
                # check if switch to 3 phases is possible
                elif (self.phases_set<3) and ((self.reserve+self.current_power)>self.switch_phase_power):
                    self.set_amp(MIN_AMP)
                    self.switch_phases(3)
                elif (self.reserve>self.step_power+UPHYSTERESIS) and (self.current_power>(self.step_power*(self.amp-1))):
                    self.set_amp(self.amp+1)
            elif self.charge_state==Charge_states.WAITING_FOR_POWER:
                if (self.reserve>self.start_power) or (self.override_amp>0):
                    self.activate_charger(True)
                    self.charge_state=Charge_states.CHARGING
                else:
                    self.activate_charger(False)
            elif self.charge_state==Charge_states.FINISHED:
                if self.current_power>FINISHEDLIMIT:
                    # restart charging
                    self.charge_state=Charge_states.CHARGING

    def __str__(self):
        state=charge_states[self.charge_state] if self.plug_state==Plug_states.PLUGGED_IN else plug_states[self.plug_state]
        return str({
            "reachable":self.reachable,
            "state":state,
            "connected phases":self.connected_phase_count,
            "car_phases":self.car_phase_count,
            "used_phases":self.used_phase_count,
            "amp":self.amp,
            "override":self.override_amp,
            "power":self.charging_power,
            "step_power":self.step_power,
            "start_power":self.start_power,
            "switch_phase_power":self.switch_phase_power,
            "mode":charger_modes[self.charge_mode],
            "alw":self.charger_activated,
            "reserve":self.reserve
        })+"\n"
        """
            "voltage":self.voltage,
            "caps":self.capabilities,
        """
