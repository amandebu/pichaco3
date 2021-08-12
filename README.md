pi charge controller

Purpose 
reads generated power from power sources and offers it to power sinks
currently supported power sources:
- S10 from E3/DC via Modbus. Modbus interface has to be enabled for this

currently supported power sinks (mutliple sinks are supported):
- go-eCharger up to HW3 including phase switching. API V1 must be enabled for local networks as well as API V2 for HW3 to enable phase switching

Install
intended to run on python3.7 on a raspberry pi

Prerequesites (pip3 install):
pymodbus commentjson

After checkout make a copy of the config.json.example to config.json and change the addresses to your local addresses.
Please also make sure that the interfaces of the devices are activated.
