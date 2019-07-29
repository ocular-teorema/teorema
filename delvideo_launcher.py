import os
from time import sleep
from delvideo import delvideo
from deleter.remover import deleter_main

VIDEO_DEL_TIMEOUT = 4 * 60 * 60

while 1:
    print('cleaning...')
    delvideo()
    deleter_main()
    print('clean ok')
    sleep(VIDEO_DEL_TIMEOUT)
