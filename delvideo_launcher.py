import os
from time import sleep
from delvideo import delvideo

VIDEO_DEL_TIMEOUT = 10 * 60

while 1:
    print('cleaning...')
    delvideo()
    print('clean ok')
    sleep(VIDEO_DEL_TIMEOUT)
