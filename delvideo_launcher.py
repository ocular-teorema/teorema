import os
from time import sleep
from delvideo import delvideo
from delvideo_addition_launcher import delvideo_addition_main

VIDEO_DEL_TIMEOUT = 4 * 60*60

while 1:
    print('cleaning...')
    delvideo()
    delvideo_addition_main()
    print('clean ok')
    sleep(VIDEO_DEL_TIMEOUT)
