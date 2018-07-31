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
import datetime
import requests

from celery import Celery
from settings import *
import psycopg2
import re
from DateTime import DateTime

#from flask_cors import CORS
from flask_restful.utils import cors
from flask_cors import CORS

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
    print(process)
    if process:
        '''
        process.kill()
        process.poll() # prevent zomdie if patched to !is_active
        '''
        print(all_cams_info)
        print(process.pid)
#       maybe this will work
#        os.kill(process.pid, 15)
        os.system('kill {}'.format(process.pid))
 
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
#                self.check_cam()
                time.sleep(2)
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
            print('worked!')
            if all_cams_info[cam]['is_active']:
                file = get_cam_path(cam[3:]) + '/theorem.conf'
                #print(file)
                with open(file, 'r') as f:
                    port = f.readlines()[1][9:].splitlines()
                    print(datetime.datetime.now())
                    try:
                        requests.get("http://127.0.0.1:{}".format(port[0]), timeout=10)
                    except:
                        print(cam, 'down')
                        process = all_cams_info[str(cam)].get('process')
                        os.system('kill ' + str(process.pid))
                        print('{} was restarted'.format(cam))
                        print(datetime.datetime.now())


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
            indefinitely='true' if req['indefinitely'] else 'false',
            janus_port=int(req['port'])+50,
            scaled_port=int(req['port'])+100,
            archive_path =  req['archive_path'] if req['archive_path'] else'/home/_VideoArchive'
        ))
#        os.system('fuser -k 8088/tcp')
#        Popen(['/opt/janus/bin/janus'])


class Cam(Resource):
    @with_lock
    def post(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        try:
            os.makedirs(os.path.join(cam_path, DBDIR))
#            os.makedirs(os.path.join(cam_path, DBDIR))
#            shutil.copy('/home/theoremg/runEnv/DB/video_analytics', os.path.join(cam_path, DBDIR, 'video_analytics'))
            save_config(req['id'], req)
            is_active = req.get('is_active', 1)
            save_cam_state(req['id'], is_active=is_active)
            all_cams_info['cam'+str(req['id'])] = {
                'is_active': is_active,
                'process': launch_process(COMMAND, os.path.join(CAMDIR, 'cam'+str(req['id']))) if is_active else None,
            } 
            with open("/opt/janus/etc/janus/janus.plugin.streaming.cfg", "a") as f:
                f.write("\n[cam {id}f restreaming sample]\ntype = rtp\ndescription = {id}f\naudio = no\nvideo = yes\nvideoport = {port}\nvideopt = 96\nvideortpmap = H264/90000\nvideofmtp = profile-level-id=42e01f\n".format(
                    id=req['id'], port=int(req['port'])+50))
                f.write(
                    "\n[cam {id} restreaming sample]\ntype = rtp\ndescription = {id}\naudio = no\nvideo = yes\nvideoport = {port}\nvideopt = 96\nvideortpmap = H264/90000\nvideofmtp = profile-level-id=42e01f\n".format(
                        id=req['id'], port=int(req['port']) + 100))
                f.close()
#                os.system('fuser -k 8088/tcp')
#                Popen(['/opt/janus/bin/janus'])
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
            delete_cam_path(cam_path)
        except Exception as e:
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        return {'status': 0}

    @with_lock
    def patch(self):
        req = request.get_json()
        cam_path = get_cam_path(req['id'])
        print(cam_path)
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

def get_time(mill):
    hours = mill//3600000
    mins =  mill//1000//60 - hours*60
#    print(hours, mins)
    return '{hh}-{mm}'.format(hh=hours, mm=mins)


class DatabaseData(Resource):
#    @cors.crossdomain(origin='*')
    def get(self, data):
        data=re.match(r"startDate=(?P<date_start>\d+-\d+-\d+) endDate=(?P<date_end>\d+-\d+-\d+) startTime=(?P<time_start>\d+-\d+) endTime=(?P<time_end>\d+-\d+) events=(?P<events>\w) cam=(?P<cam>\w+)", data.replace('&', ' '))
        data = data.groupdict()
#        print(data)
        conn = psycopg2.connect("dbname='video_analytics' user='va' password=''")
        cur =conn.cursor()
        start_time_database=' start_time >=' + str((int(data['time_start'][0:2])*60+int(data['time_start'][3:]))*60*999) +' and 'if data['time_start'] != '00-00' else ''
        end_time_database=' end_time <= ' + str((int(data['time_end'][0:2])*60+int(data['time_end'][3:]))*60*1001) +' and 'if data['time_end'] != '00-00' else ''
        start_date_database=' date >= '+ str(DateTime(data['date_start'].replace('-', '/') + ' UTC').JulianDay()) +' and '
        end_date_database = ' date <= ' + str(DateTime(data['date_end'].replace('-', '/') + ' UTC').JulianDay()) +' and '
        cam = "records.cam='{}'".format(data['cam'])
        cur.execute('select start_time,end_time,date, video_archive,cam,id  from records where' + start_date_database + end_date_database + start_time_database + end_time_database + cam + ';' )
        data_out=cur.fetchall()
        result = []
        event_types = "and type = {}".format(data['events']) if int(data['events']) > 0 else ''
        for el in data_out:
            r = { 'date':el[2], 'start':get_time(el[0]), 'end':get_time(el[1]), 'archivePostfix': el[3],  'cam':el[4], 'id':el[5]}
            result.append(r)
            conn.close()
        for el in result:
            conn=psycopg2.connect("dbname='video_analytics' user='va' password=''")
            cur = conn.cursor()
            cur.execute("select id, cam, archive_file1, archive_file2, start_timestamp, end_timestamp, type, confidence,reaction,file_offset_sec from events where events.cam='{cam}' and date={date} and archive_file1='{archive}'  {events};".format(cam=el['cam'], date=el['date'], archive=el['archivePostfix'], events=event_types))
            rows=cur.fetchall()
            list = []
            for event in rows:
                list.append({'id':event[0], 'cam':event[1], 'archiveStartHint':event[2], 'archiveEndHint':event[3], 'startTimeMS':event[4],'endTimeMS':event[5],'eventType':event[6], 'confidence':event[7], 'reaction': event[8], 'offset': event[9]})
            el['events']=list
            conn.close()
        return result


class DatabaseEventsData(Resource):
    def get(self, data):
        data=re.match(r"startDate=(?P<date_start>\d+-\d+-\d+) endDate=(?P<date_end>\d+-\d+-\d+) startTime=(?P<time_start>\d+) endTime=(?P<time_end>\d+) cam=(?P<cam>\w+)", data.replace('&', ' '))
        data=data.groupdict()
        conn = psycopg2.connect("dbname='video_analytics' user='va' password=''")
        cur = conn.cursor()
        start_date_database=' date >= '+ str(DateTime(data['date_start'].replace('-', '/') + ' UTC').JulianDay()) +' and '
        end_date_database = ' date <= ' + str(DateTime(data['date_end'].replace('-', '/') + ' UTC').JulianDay()) +' and '
        cur.execute("select id, cam, archive_file1, archive_file2, start_timestamp, end_timestamp, type, confidence, reaction,date,file_offset_sec from events where events.cam='{cam}'".format(cam=data['cam'])+ ' and'+start_date_database+end_date_database+'start_timestamp >='+data['time_start']+' and ' + 'end_timestamp <=' + data['time_end'] + ';')
        rows=cur.fetchall()
        list = []
        for event in rows:
                list.append({'id':event[0], 'cam':event[1], 'archiveStartHint':event[2], 'archiveEndHint':event[3], 'startTimeMS':event[4],'endTimeMS':event[5],'eventType':event[6], 'confidence':event[7], 'reaction': event[8], 'date': event[9], 'offset': event[10]})
        conn.close()
        return list
        
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
#os.system('fuser -k 8088/tcp')
#Popen(['/opt/janus/bin/janus'])

lock = Lock()

all_cams_info = {}
if 'celery' not in sys.argv[0]:
    launch_cameras()

    ControlPi().start()


app = Flask(__name__)
#app=CORS(app)

api = Api(app)
#api = CORS(api)
api.add_resource(Cam, '/')
api.add_resource(Stat, '/stat')
api.add_resource(DatabaseData, '/db/<string:data>', endpoint='db_data')
api.add_resource(DatabaseEventsData, '/archivedb/<string:data>', endpoint='db_arhcive_data')

app.config.update(
    CELERY_BROKER_URL='amqp://teorema:teorema@0.0.0.0:5672//',
    CELERY_RESULT_BACKEND='amqp://teorema:teorema@0.0.0.0:5672//'
)

@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    print('zzzzzz================================')
    return response


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
