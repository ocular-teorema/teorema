import os
from time import sleep
from delvideo import delvieo

VIDEO_DEL_TIMEOUT = 4 * 60*60

while 1:
    print('cleaning...')
    delvideo()
    print('clean ok')
    sleep(VIDEO_DEL_TIMEOUT)
