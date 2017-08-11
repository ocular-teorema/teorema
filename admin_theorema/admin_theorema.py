#!/usr/bin/python3
from os import listdir
from os.path import join, isfile
import subprocess
import sqlite3
import time
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer

from settings import *

COMMAND = 'python3 /home/egor/Projects/teorema/admin_theorema/test.py'
COMMAND = 'sleep 500'
PORT = 8888


def parse_config(path):
    print('parsing', path)
    return {}

def launch_process(command, cwd):
    print('launch process')
    return subprocess.Popen(command.split(), cwd=cwd)

cams = [f for f in listdir(CAMDIR) if not isfile(join(CAMDIR, f))]

all_cams_info = {}

for cam in cams:
    all_cams_info[cam] = {}
    all_cams_info[cam]['process'] = launch_process(COMMAND, join(CAMDIR, cam))

print(all_cams_info)

while True:
    time.sleep(1)
    for cam, cam_info in all_cams_info.items():
        if cam_info['process'].poll() is not None:
            cam_info['process'] = launch_process(COMMAND, join(CAMDIR, cam))



