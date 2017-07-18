#!/usr/bin/python3
from os import listdir
from os.path import join, isfile
import subprocess
import sqlite3
import time
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer


CAMDIR = '/home/processInstances'
ARCHDIR = '/home/VideoArchive'
CONFIG_NAME = 'theorem.conf'
DBDIR = 'DB'
COMMAND = 'python3 /home/egor/Projects/teorema/admin_theorema/test.py'
COMMAND = 'sleep 500'
PORT = 8888


def parse_config(path):
    print('parsing', path)
    return {}

def update_config(conf_path, new_config):
    print('updating config for', conf_path)
    return

def load_config(cam):
    print('loading config for', cam)
    return {}

def launch_process(command, cwd):
    print('launch process')
    return subprocess.Popen(command.split(), cwd=cwd)

cams = [f for f in listdir(CAMDIR) if not isfile(join(CAMDIR, f))]

all_cams_info = {}

for cam in cams:
    all_cams_info[cam] = {}
    print('processing', cam)

    conf_path = join(CAMDIR, cam, CONFIG_NAME)
    all_cams_info[cam]['config'] = parse_config(conf_path)
    new_config = load_config(cam)
    if new_config and new_config != all_cams_info[cam]['config']:
        update_config(conf_path, new_config)
        all_cams_info[cam]['config'] = new_config

# work with events db
#    db_path = join(CAMDIR, DBDIR)

    all_cams_info[cam]['process'] = launch_process(COMMAND, join(CAMDIR, cam))


# launch web server for commands
# https://gist.github.com/gnilchee/246474141cbe588eb9fb
class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

server = ThreadingSimpleServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)

while 1:
    print('zz')
    server.handle_request()

print(all_cams_info)

while True:
    time.sleep(1)
    for cam, cam_info in all_cams_info.items():
        if cam_info['process'].poll() is not None:
            cam_info['process'] = launch_process(COMMAND, join(CAMDIR, cam))



