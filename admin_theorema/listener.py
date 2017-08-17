import os
import shutil
from threading import Lock, Thread
import time
import json
from subprocess import Popen, PIPE
from flask import Flask, request
from flask_restful import Resource, Api


from settings import *


def get_cam_saved_state(numeric_id):
    with open(os.path.join(get_cam_path(numeric_id), ADDITIONAL_CONFIG), 'r') as f:
        result = json.loads(f.read())
    return result

def get_cam_path(numeric_id):
    return os.path.join(CAMDIR, 'cam'+str(numeric_id))

def get_filesystem_info():
    # man df
    return Popen(['df', ARCHDIR], stdout=PIPE).communicate()[0].decode().split()[-5:-2]

def launch_process(command, cwd):
    return Popen(command.split(), cwd=cwd)

def get_saved_cams():
    return [f for f in os.listdir(CAMDIR) if not os.path.isfile(os.path.join(CAMDIR, f))]

def save_cam_state(numeric_id, **kwargs):
    with open(os.path.join(get_cam_path(numeric_id), ADDITIONAL_CONFIG), 'w') as f:
        f.write(json.dumps(kwargs))

def process_died(process):
    return process is None or process.poll() is not None

def stop_cam(numeric_id):
    all_cams_info['cam'+str(numeric_id)].is_active = False
    process = all_cams_info['cam'+str(numeric_id)].get('process')
    if process:
        process.kill()
        all_cams_info['cam'+str(numeric_id)].pop('process')

def with_lock(func):
    def result(*args, **kwargs):
        with lock:
            func(*args, **kwargs)
    return result


class ControlPi(Thread):
    def run(self):
        while True:
            try:
                self.check_processes()
                time.sleep(LAG)
            except Exception as e:
                print(str(e))

    @with_lock
    def check_processes(self):
        print('zzzz')
        for cam, cam_info in all_cams_info.items():
            if cam_info['is_active'] and process_died(cam_info['process']):
                cam_info['process'] = launch_process(COMMAND, os.path.join(CAMDIR, cam))
        

def save_config(numeric_id, req):
    with open(os.path.join(get_cam_path(numeric_id), CONFIG_NAME), 'w') as f:
        f.write(TEMPLATE.format(**req))

class Cam(Resource):
    @with_lock
    def post(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        try:
            os.makedirs(os.path.join(cam_path, DBDIR))
            save_config(req['id'], req)
            is_active = req.get('is_active', 1)
            save_cam_state(req['id'], is_active=is_active)
            all_cams_info['cam'+req['id']] = {
                'is_active': is_active,
                'process' = launch_process(COMMAND, os.path.join(CAMDIR, 'cam'+req['id'])) if is_active else None,
            }
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}

    @with_lock
    def delete(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        try:
            stop_cam(req['id'])
            all_cams_info.pop('cam'+req['id'])
            shutil.rmtree(cam_path)
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}

    @with_lock
    def patch(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        stop_cam(req['id'])
        try:
            save_config(req['id'], req)
            stop_cam(req['id'])
            save_cam_state(req['id'], is_active=req.get('is_active', 1))
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}



class Stat(Resource):
    def get(request):
        print(all_cams_info)
        try:
            return {
                'message': get_filesystem_info(),
                'status': 0
            }
        except Exception as e:
            return {'status': 1, 'message': str(e)}


@with_lock
def launch_cameras():
    for cam in get_saved_cams():
        all_cams_info[cam] = {}
        is_active = get_cam_saved_state(cam[3:])['is_active']
        all_cams_info[cam]['is_active'] = is_active
        if is_active:
            all_cams_info[cam]['process'] = launch_process(COMMAND, os.path.join(CAMDIR, cam))
        else:
            all_cams_info[cam]['process'] = None


lock = Lock()

all_cams_info = {}
launch_cameras()

ControlPi().start()


app = Flask(__name__)
api = Api(app)
api.add_resource(Cam, '/')
api.add_resource(Stat, '/stat')

# this dont work properly with background thread. use EXPORT FLASK_APP=listener.py && flask run
#if __name__ == '__main__':
#    app.run(debug=True)
