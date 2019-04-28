import os
from time import sleep

VIDEO_DEL_TIMEOUT = 4 * 60*60

while 1:
    sleep(VIDEO_DEL_TIMEOUT)
    os.system('cd /home/_VideoArchive && /usr/local/scripts/delvideo_new.sh')
