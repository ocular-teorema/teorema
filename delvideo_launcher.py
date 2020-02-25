import os
from time import sleep
from delvideo import delvideo
from deleter.remover import deleter_main
from datetime import datetime

VIDEO_DEL_TIMEOUT = 60 * 60

while 1:
    print('cleaning... at', str(datetime.isoformat(datetime.now(), sep='_'))[:19], flush=True)
    delvideo()
    deleter_main()
    print('clean ok at', str(datetime.isoformat(datetime.now(), sep='_'))[:19], flush=True)
    sleep(VIDEO_DEL_TIMEOUT)
