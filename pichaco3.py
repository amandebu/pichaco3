import time
import commentjson
from controller import Controller
import logging
logger = logging.getLogger('pichaco3')
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
#logging.basicConfig(encoding='utf-8', level=logging.INFO)

with open('config.json') as json_file:
    config = commentjson.load(json_file)
controller=Controller("Pichaco3",config)
nexttick=round(time.time(),0)
while True:
    if nexttick<=time.time():
        controller.do_control(nexttick)
        nexttick+=1
        logger.debug(controller)
    time.sleep(0.1)
