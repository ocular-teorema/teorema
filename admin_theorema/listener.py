import os
import shutil
import _thread
import time
from subprocess import Popen, PIPE
from flask import Flask, request
from flask_restful import Resource, Api


from settings import *

app = Flask(__name__)
api = Api(app)


def get_cam_path(req):
    return os.path.join(CAMDIR, 'cam'+str(req['id']))


def get_filesystem_info():
        # man df
        return Popen(['df', ARCHDIR], stdout=PIPE).communicate()[0].decode().split()[-5:-2]

def launch_process(command, cwd):
    print('launch process')
    return Popen(command.split(), cwd=cwd)


def control_pi(all_cams_info):
    for cam in [f for f in os.listdir(CAMDIR) if not os.path.isfile(os.path.join(CAMDIR, f))]:
        all_cams_info[cam] = {}
        all_cams_info[cam]['process'] = launch_process(COMMAND, os.path.join(CAMDIR, cam))
        all_cams_info[cam]['is_active'] = True

    while True:
        time.sleep(1)
        for cam, cam_info in all_cams_info.items():
            if cam_info['process'].poll() is not None and cam_info['is_active']:
                cam_info['process'] = launch_process(COMMAND, os.path.join(CAMDIR, cam))



def stop_cam(numeric_id):
    all_cams_info['cam'+str(numeric_id)].is_active = False
    process = all_cams_info['cam'+str(numeric_id)].get('process')
    if process:
        process.kill()
        all_cams_info['cam'+str(numeric_id)].pop('process')


class Cam(Resource):
    def post(self):
        req = request.get_json()
        cam_path = get_cam_path(req)
        try:
            os.makedirs(os.path.join(cam_path, DBDIR))
            f = open(os.path.join(cam_path, CONFIG_NAME), 'w')
            f.write('\n'.join(['{}={}'.format(k, v) for k, v in req.items()]))
            f.close()
            f = open(os.path.join(cam_path, ADDITIONAL_CONFIG), 'w')
            f.write(req['is_active'])
            f.close()
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}

    def delete(self):
        req = request.get_json()
        cam_path = get_cam_path(req)
        try:
            stop_cam(req['id'])
            all_cams_info.pop('cam'+req['id'])
            shutil.rmtree(cam_path)
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}

    def patch(self):
        req = request.get_json()
        cam_path = get_cam_path(req)
        stop_cam(req['id'])
        try:
            f = open(os.path.join(cam_path, CONFIG_NAME), 'w')

            f.close()
            if req['is_active']:        
                start_cam(req['id'])
            else:
                stop_cam(req['id'])
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
            

api.add_resource(Cam, '/')
api.add_resource(Stat, '/stat')

all_cams_info = {}
_thread.start_new_thread(control_pi, (all_cams_info,))

if __name__ == '__main__':
    app.run(debug=True)
