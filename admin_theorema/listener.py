import sys
import traceback
import os
import shutil
from threading import Lock, Thread
import time
import json
from subprocess import Popen, PIPE
from flask import Flask, request
from flask_restful import Resource, Api
import socket

from celery import Celery
from settings import *


def get_cam_saved_state(numeric_id):
    with open(os.path.join(get_cam_path(numeric_id), ADDITIONAL_CONFIG), 'r') as f:
        result = json.loads(f.read())
    return result

def get_cam_path(numeric_id):
    return os.path.join(CAMDIR, 'cam'+str(numeric_id))

def get_filesystem_info():
    # man df
    return Popen(['df', '/home/_VideoArchive'], stdout=PIPE, stderr=PIPE).communicate()[0].decode().split()[-5:-2]

def launch_process(command, cwd):
    return Popen(command.split(), cwd=cwd, stdout=PIPE, stderr=PIPE)

def get_saved_cams():
    return [f for f in os.listdir(CAMDIR) if not os.path.isfile(os.path.join(CAMDIR, f))]

def save_cam_state(numeric_id, **kwargs):
    with open(os.path.join(get_cam_path(numeric_id), ADDITIONAL_CONFIG), 'w') as f:
        f.write(json.dumps(kwargs))

def process_died(process):
    return process is None or process.poll() is not None

def stop_cam(numeric_id):
    process = all_cams_info['cam'+str(numeric_id)].get('process')
    if process:
        process.kill()
        process.poll() # prevent zomdie if patched to !is_active

def with_lock(func):
    def result(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)
    return result


class ControlPi(Thread):
    def run(self):
        while True:
            try:
                self.check_processes()
                self.check_cam()
                time.sleep(LAG)
            except Exception as e:
                print('\n'.join(traceback.format_exception(*sys.exc_info())))

    @with_lock
    def check_processes(self):
        for cam, cam_info in all_cams_info.items():
            if cam_info['is_active'] and process_died(cam_info['process']):
                cam_info['process'] = launch_process(COMMAND, os.path.join(CAMDIR, cam))
    @with_lock
    def check_cam(self):
        for cam in get_saved_cams():
            #print(cam)
            if all_cams_info[cam]['is_active']:
                file = get_cam_path(cam[3:]) + '/theorem.conf'
                #print(file)
                with open(file, 'r') as f:
                    port = f.readlines()[1][9:]
                    #print(port)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if sock.connect_ex(('127.0.0.1', int(port))) != 0:
                        print(cam+'down')
                        stop_cam(cam[3:])
                        launch_process(COMMAND, os.path.join(CAMDIR, cam))
                        print('{} was restarted'.format(cam))
                    sock.close()        



def save_config(numeric_id, req):
    with open(os.path.join(get_cam_path(numeric_id), CONFIG_NAME), 'w') as f:
        f.write(TEMPLATE.format(
            port = req['port'],
            id = req['id'],
            name = req['name'],
            address = req['address'],
            fps = req['fps'],
            storage_life = req['storage_life'] if not req['indefinitely'] else 1000,
            compress_level = req['compress_level'] + 27,
            downscale_coeff = [0.5, 0.3, 0.25, 0.15, 0.15, 0.15][req['resolution'] - 1],
#            global_scale = [1.0, 1.0, 1.0, 1.0, 0.5, 0.25][req['resolution'] - 1],
            global_scale = [0.5, 0.5, 0.5, 0.5, 0.25, 0.125][req['resolution'] - 1],
            motion_analysis = 'true' if req['analysis'] > 2 else 'false',
            diff_analysis = 'true' if req['analysis'] > 1 else 'false',
            indefinitely='true' if req['indefinitely'] else 'false'
        ))


class Cam(Resource):
    @with_lock
    def post(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        try:
            os.makedirs(os.path.join(cam_path, DBDIR))
            shutil.copy('/home/theoremg/runEnv/DB/video_analytics', os.path.join(cam_path, DBDIR, 'video_analytics'))
            save_config(req['id'], req)
            is_active = req.get('is_active', 1)
            save_cam_state(req['id'], is_active=is_active)
            all_cams_info['cam'+str(req['id'])] = {
                'is_active': is_active,
                'process': launch_process(COMMAND, os.path.join(CAMDIR, 'cam'+str(req['id']))) if is_active else None,
            }
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())))
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        return {'status': 0}

    @with_lock
    def delete(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        try:
            stop_cam(req['id'])
            all_cams_info.pop('cam' + str(req['id']))
            delete_cam_path.apply_async((cam_path,))
        except Exception as e:
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        return {'status': 0}

    @with_lock
    def patch(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        try:
            save_config(req['id'], req)
            save_cam_state(req['id'], is_active=req.get('is_active', 1))
            all_cams_info['cam'+str(req['id'])]['is_active'] = req.get('is_active', 1)
            stop_cam(req['id'])
        except Exception as e:
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        return {'status': 0}



class Stat(Resource):
    def get(request):
        try:
            return {
                'message': get_filesystem_info(),
                'status': 0
            }
        except Exception as e:
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}


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

os.system('kill `pidof processInstance`')

lock = Lock()

all_cams_info = {}
if 'celery' not in sys.argv[0]:
    launch_cameras()

    ControlPi().start()


app = Flask(__name__)
api = Api(app)
api.add_resource(Cam, '/')
api.add_resource(Stat, '/stat')


app.config.update(
    CELERY_BROKER_URL='amqp://teorema:teorema@0.0.0.0:5672//',
    CELERY_RESULT_BACKEND='amqp://teorema:teorema@0.0.0.0:5672//'
)


def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


celery = make_celery(app)

@celery.task(bind=True, name = 'delete_cam')
def delete_cam_path(self, cam_path):

    shutil.rmtree(cam_path)

    print('Камера Успешно удалена')

'''
def check_cam(all_cams_info):
    for cam in get_saved_cams():
        if all_cams_info[cam]['is_active']:
            print(cam)
            print(all_cams_info[cam]['is_active'])
            file = get_cam_path(cam[3:]) + '/theorem.conf'
            with open(file, 'r') as f:
                port = f.readlines()[1][9:]
                sock = socket.socket()
                if sock.connect_ex(('127.0.0.1', int(port))) == 0:
                    stop_cam(cam[3:])
                    launch_process(COMMAND, os.path.join(CAMDIR, cam))
                    print('{} was restarted'.format(cam))
    print('{} works fine'.format('all'))
'''




# this dont work properly with background thread. use EXPORT FLASK_APP=listener.py && flask run
#if __name__ == '__main__':
#    app.run(debug=True)
