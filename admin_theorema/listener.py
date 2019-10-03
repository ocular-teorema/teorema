import sys
import traceback
import os
import shutil
from threading import Lock, Thread
import time
import json
from subprocess import Popen, PIPE
from flask import Flask, request
from flask_restful import Resource, Api, reqparse
import socket
import datetime
import requests
import base64
import subprocess
from celery import Celery
from settings import *
import psycopg2
import re
from DateTime import DateTime
import julian
import configparser
from PIL import Image
import io


from flask_restful.utils import cors
from flask_cors import CORS
from flask import make_response

SUPERVISOR_ERROR_TEXT = '''
        Need to interact with supervisor.
        1) Set permissions to socket file. 
        Open your supervisord.conf and in [unix_http_server] section write:
        chmod=0770
        chown=root:%group you run this listener%
        After this, restart supervisord.
        2) Set permissions to config file:
        touch /etc/supervisor/conf.d/cameras.conf
        chown root:%group you run this listener% /etc/supervisor/conf.d/cameras.conf
        chmod 660 /etc/supervisor/conf.d/cameras.conf

'''

CAM_PREFIX = 'cam'
QUAD_PREFIX = 'quad'
VIDEO_DIR = '/home/_VideoArchive'

def get_obj_name(numeric_id, obj_type):
    return obj_type + str(numeric_id)

def get_path(obj_name):
    return os.path.join(CAMDIR, obj_name)

def get_filesystem_info():
    return Popen(['df', '/home/_VideoArchive'], stdout=PIPE, stderr=PIPE).communicate()[0].decode().split()[-5:-2]

def with_lock(func):
    def result(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)
    return result



def save_cam_config(path, req):
    with open(os.path.join(path, CONFIG_NAME), 'w') as f:
        f.write(TEMPLATE.format(
            port = req['port'],
            id = req['id'],
            name = req['name'],
            address = req['address'],
            fps = 0, # req['fps']
            storage_life = req['storage_life'] if not req['indefinitely'] else 1000,
            compress_level = req['compress_level'] + 27,
            downscale_coeff = 0, #[0.5, 0.3, 0.25, 0.15, 0.15, 0.15][req['resolution'] - 1],
            global_scale = 0.5, #[0.5, 0.5, 0.5, 0.5, 0.25, 0.125][req['resolution'] - 1],
            motion_analysis = 'true' if req['analysis'] > 2 else 'false',
            diff_analysis = 'true' if req['analysis'] > 1 else 'false',
            indefinitely='true' if req['indefinitely'] else 'false',
            output_port = int(req['port']) + 50,
            archive_path =  req['archive_path'] if req['archive_path'] else'/home/_VideoArchive'
        ))

def save_quad_config(path, req):
    with open(os.path.join(path, QUAD_CONFIG_NAME), 'w') as f:
        f.write(json.dumps({
                "outputUrl1":    'ws://localhost:%s' % req['port'],
                "outputUrl2": "rtmp://localhost:1935/vasrc/quad%s" % req['id'],
                "outputWidth":  req['output_width'],
                "outputHeight": req['output_height'],
                "outputFps":    req['output_FPS'],
                "outputCrf":    req['output_quality'],
                "borderWidth":  4,
                "camList": [
                        {
                                "name": cam['name'],
                                "posX": cam['posX'],
                                "posY": cam['posY'],
                                "width": cam['width'],
                                "height": cam['height'],
                                "streamUrl": 'rtmp://localhost:1935/vasrc/cam%s' % cam['port']
                        } for cam in req['cameras']
                ]
        }, indent=4))


def save_config(obj_type, path, req):
    if obj_type == 'cam':
        return save_cam_config(path, req)
    elif obj_type == 'quad':
        return save_quad_config(path, req)
    else:
        raise Exception('unknown type')

def add_autostart(obj_type, obj_name, path):
    if obj_type == 'cam':
        command = '/usr/bin/processInstance'
    elif obj_type == 'quad':
        command = '/usr/bin/kvadrator %s' % os.path.join(path, 'config.json')
    config['program:%s' % obj_name] = {
            'command': command,
            'directory': path,
            'autostart': 'true',
            'autorestart': 'true',
            'redirect_stderr': 'true',
            'user': 'www-data',
            'startretries': 9999999,
    }
    save_supervisor_config()

def del_autostart(obj_name):
    config.pop('program:%s' % obj_name, None)
    save_supervisor_config()

class Cam(Resource):
    @with_lock
    def post(self):
        req = request.get_json()
        obj_type = req.get('type', 'cam')
        obj_name = get_obj_name(req['id'], obj_type)
        path = get_path(obj_name)
        try:
            os.makedirs(path)
            save_config(obj_type, path, req)
            is_active = req.get('is_active', 1)
            if is_active:
                add_autostart(obj_type, obj_name, path)

        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        print('post ok', flush=True)
        return {'status': 0}

    @with_lock
    def delete(self):
        req = request.get_json()
        obj_type = req.get('type', 'cam')
        obj_name = get_obj_name(req['id'], obj_type)
        path = get_path(obj_name)
        try:
            del_autostart(obj_name)
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        try:
            delete_path(path)
        except FileNotFoundError as e:
            pass
        return {'status': 0}

    @with_lock
    def patch(self):
        req = request.get_json()
        obj_type = req.get('type', 'cam')
        obj_name = get_obj_name(req['id'], obj_type)
        path = get_path(obj_name)
        try:
            save_config(obj_type, path, req)
            is_active = req.get('is_active', 1)
            if is_active and 'program:%s'%obj_name in config.sections():
                print('restarting %s due to potential config changes'%obj_name, flush=True)
                os.system('supervisorctl restart %s'%obj_name)
            else:
                if is_active:
                    add_autostart(obj_type, obj_name, path)
                else:
                    del_autostart(obj_name)
        except Exception as e:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}
        return {'status': 0}


class Stat_fs(Resource):
    def get(self):
        try:
            return {
                'message': get_filesystem_info(),
                'status': 0
            }
        except Exception as e:
            return {'status': 1, 'message': '\n'.join(traceback.format_exception(*sys.exc_info()))}


class Stat(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('startTs', type=str)
        parser.add_argument('endTs', type=str)
        parser.add_argument('cameras', type=str)
        args = parser.parse_args()
        print(args, flush=True)

        start_time = args['startTs']
        end_time = args['endTs']
        cameras_list = args['cameras'].split(',')
        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
        cur = conn.cursor()

        cameras = []
        for x in range(len(cameras_list)):
            cameras.append("'cam{}'".format(cameras_list[x]))

        cameras_database = 'events.cam in ' + '({})'.format(', '.join(cameras))

        cur.execute("select type, confidence, reaction  from events where {cam}".format(cam=cameras_database)
                    + ' and  start_timestamp >=' + str(start_time) + ' and ' + 'end_timestamp <=' + str(end_time) + ';')

        rows = cur.fetchall()
        conn.close()

        react_stat = {'-1': 0, '1': 0, '2': 0}
        types_stat = {'1': 0, '2': 0, '4': 0, '8': 0}
        confidence_stat = {'low': 0, 'medium': 0, 'high': 0}

        for event in rows:
            event_type = event[0]
            confidence = event[1]
            reaction = event[2]

            types_stat[str(event_type)] += 1
            react_stat[str(reaction)] += 1

            if confidence >= 80:
                confidence_stat['high'] += 1
            elif confidence >= 50:
                confidence_stat['medium'] += 1
            else:
                confidence_stat['low'] += 1

        result = {
            "react": react_stat,
            "types": types_stat,
            "confidence": confidence_stat
        }
        print(result)
        return result


def get_time(mill):
    hours = mill//3600000
    mins =  mill//1000//60 - hours*60
    return '{hh}-{mm}'.format(hh=hours, mm=mins)


class DatabaseData(Resource):
#    @cors.crossdomain(origin='*')
    def get(self, data):
        data=re.match(r"startDate=(?P<date_start>\d+-\d+-\d+) endDate=(?P<date_end>\d+-\d+-\d+) startTime=(?P<time_start>\d+-\d+) endTime=(?P<time_end>\d+-\d+) events=(?P<events>\w) cam=(?P<cam>\w+)", data.replace('&', ' '))
        data = data.groupdict()
        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
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
        print(data_out)
        print("start")
        print(str(DateTime(data['date_start'].replace('-', '/') + ' UTC').JulianDay()))
        print(str(DateTime(data['date_end'].replace('-', '/') + ' UTC').JulianDay()))
        print(len(data_out))
        if len(data_out)>0:
            for el in data_out:
                r = { 'date':el[2], 'start':get_time(el[0]), 'end':get_time(el[1]), 'archivePostfix': el[3],  'cam':el[4], 'id':el[5]}
                result.append(r)
                conn.close()
            for el in result:
                conn=psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
                cur = conn.cursor()
                cur.execute("select id, cam, archive_file1, archive_file2, start_timestamp, end_timestamp, type, confidence,reaction,file_offset_sec from events where events.cam='{cam}' and date={date} and archive_file1='{archive}'  {events};".format(cam=el['cam'], date=el['date'], archive=el['archivePostfix'], events=event_types))
                rows=cur.fetchall()
                list = []
                for event in rows:
                    list.append({'id':event[0], 'cam':event[1], 'archiveStartHint':event[2], 'archiveEndHint':event[3], 'startTimeMS':event[4],'endTimeMS':event[5],'eventType':event[6], 'confidence':event[7], 'reaction': event[8], 'offset': event[9]})
                el['events']=list
                conn.close()
        else:
            id = 1
            try:
                dir_data = subprocess.check_output("ls", cwd="/home/_VideoArchive/{}".format(data['cam']))
                dir_data = dir_data.decode()
                dir_data=dir_data.split('\n')
                dir_data.remove("alertFragments")
                dir_data.remove('') if "" in dir_data else None
                for row in dir_data:
                    print(row)
                    data_dict=re.match(r"cam(?P<cam>\d+)_(?P<date>\d+_\d+_\d+)___(?P<time>\d+_\d+_\d+)", row)
                    data_dict=data_dict.groupdict()
                    juliandate = round(julian.to_jd(datetime.datetime.strptime(data_dict["date"], "%d_%m_%Y")+ datetime.timedelta(hours=int(data_dict["time"][:2]), minutes=int(data_dict["time"][3:5]), seconds=30)))
                    starttime = int(int(data_dict["time"][:2]) * 60 + int(data_dict["time"][3:5])) * 60 * 1000
                    endtime = (int(int(data_dict["time"][:2]) * 60 + int(data_dict["time"][3:5])) * 60 * 1000)+600000
                    print(int(int(data['time_end'][0:2]) * 60 + int(data['time_end'][3:]))*60*1000)
                    print(endtime)
                    if ( round(DateTime(data['date_start'].replace('-', '/') + ' UTC').JulianDay()) <= juliandate and
                            round(DateTime(data['date_end'].replace('-', '/') + ' UTC').JulianDay()) >= juliandate and
                            int(int(data['time_end'][0:2]) * 60 + int(data['time_end'][3:])) * 60 * 1001 >= endtime and
                            int(int(data['time_start'][0:2]) * 60 + int(data['time_start'][3:])) * 60 * 999 <= starttime
                    ):
                        result.append({
                            'id':id,
                            'cam':'cam'+data_dict["cam"],
                            'archivePostfix':'/cam'+data_dict['cam']+'/'+row,
                            'date' : juliandate,
                            'start':data_dict["time"][0:5].replace('_', '-'),
                        'end':endtime,
                        'events':[]})
                        id += 1
#                    print(result)
            except:
                pass
        return result


class DatabaseEventsData(Resource):
    def get(self, data):
        data=re.match(r"startDate=(?P<date_start>\d+-\d+-\d+) endDate=(?P<date_end>\d+-\d+-\d+) startTime=(?P<time_start>\d+) endTime=(?P<time_end>\d+) cam=(?P<cam>\w+)", data.replace('&', ' '))
        data=data.groupdict()
        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
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


class ArchiveEvents(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('startTs', type=str)
        parser.add_argument('endTs', type=str)
        parser.add_argument('cameras', type=str)
        parser.add_argument('react', type=str)
        parser.add_argument('types', type=str)
        parser.add_argument('conf_low', type=int)
        parser.add_argument('conf_medium', type=int)
        parser.add_argument('conf_high', type=int)
        parser.add_argument('skip', type=int)
        parser.add_argument('limit', type=int)
        args = parser.parse_args()
        print(args, flush=True)

        start_time = args['startTs']
        end_time = args['endTs']
        cameras_list = args['cameras'].split(',')
        reactions = args['react']
        event_types = args['types']
        conf_low = args['conf_low']
        conf_medium = args['conf_medium']
        conf_high = args['conf_high']
        skip = args['skip'] if args['skip'] else 0
        limit = args['limit'] if args['limit'] else 100

        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
        cur = conn.cursor()

        cameras = []
        for x in range(len(cameras_list)):
            cameras.append("'cam{}'".format(cameras_list[x]))

        cameras_database = 'events.cam in ' + '({})'.format(', '.join(cameras))
        types_db = ' and type in ({})'.format(event_types)
        reacts_db = ' and reaction in ({})'.format(reactions)

        confidence_db = ' and confidence '

        if conf_low:
            if conf_medium:
                if not conf_high:
                    confidence_db += '< 80 '
                else:
                    confidence_db = ''
            else:
                confidence_db += '< 50 ' if not conf_high else 'not between 50 and 79 '
        else:
            if conf_medium:
                confidence_db += 'between 50 and 79 ' if not conf_high else '>= 59'
            else:
                if conf_high:
                    confidence_db += '>= 80 '
                else:
                    return {'status': 1, 'message': 'at least one confidence level must be passed'}

        cur.execute("select id,cam,archive_file1,archive_file2,start_timestamp,end_timestamp,type,confidence,reaction,date,file_offset_sec from events where {cam}"
                    .format(cam=cameras_database) + ' and  start_timestamp >=' + str(start_time) + ' and ' + 'end_timestamp <=' + str(end_time)
                    + confidence_db + types_db + reacts_db + 'offset {offset_int} limit {limit_int};'
                    .format(offset_int=skip, limit_int=limit))

        rows = cur.fetchall()
        conn.close()


        result = []
        for event in rows:
            result.append({'id': event[0],
                           'cam': event[1],
                           'archiveStartHint': event[2],
                           'archiveEndHint': event[3],
                           'startTs': event[4],
                           'endTs': event[5],
                           'type': event[6],
                           'conf': event[7],
                           'react': event[8],
                           'date': event[9],
                           'offset': event[10]
                           }
                          )
        return result


class ArchiveVideo(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('startTs', type=str)
        parser.add_argument('endTs', type=str)
        parser.add_argument('cameras', type=str)
        parser.add_argument('skip', type=int)
        parser.add_argument('limit', type=int)
        args = parser.parse_args()
        print(args, flush=True)

        start_time = args['startTs']
        end_time = args['endTs']
        cameras_list = args['cameras'].split(',')
        skip = args['skip'] if args['skip'] else 0
        limit = args['limit'] if args['limit'] else 100

        start_dt = datetime.datetime.fromtimestamp(int(start_time[:-3]))
        end_dt = datetime.datetime.fromtimestamp(int(end_time[:-3]))
        start_dt_time = start_dt.time().strftime('%H:%M')
        end_dt_time = end_dt.time().strftime('%H:%M')
        start_dt_date = start_dt.date().strftime('%Y-%m-%d')
        end_dt_date = end_dt.date().strftime('%Y-%m-%d')

        start_time_db = ' and start_time >=' + str((int(start_dt_time[0:2]) * 60 + int(start_dt_time[3:])) * 60 * 999)\
            if start_dt_time != '00-00' else ''
        end_time_db = ' and end_time >=' + str((int(end_dt_time[0:2]) * 60 + int(end_dt_time[3:])) * 60 * 999) \
            if end_dt_time != '00-00' else ''

        start_date_db = ' and date >= ' + str(DateTime(start_dt_date.replace('-', '/') + ' UTC').JulianDay())
        end_date_db = ' and date <= ' + str(DateTime(end_dt_date.replace('-', '/') + ' UTC').JulianDay())

        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
        cur = conn.cursor()

        cameras = []
        for x in range(len(cameras_list)):
            cameras.append("'cam{}'".format(cameras_list[x]))

        cameras_database = 'records.cam in ' + '({})'.format(', '.join(cameras))

        cur.execute("select start_time,end_time,date, video_archive,cam,id from records where {cam}"
                    .format(cam=cameras_database) + str(start_time_db) + str(end_time_db) + str(start_date_db + str(end_date_db))
                    + ' order by date,start_time offset {offset_int} limit {limit_int};'.format(offset_int=skip, limit_int=limit))

        rows = cur.fetchall()
        conn.close()

        result = []
        for record in rows:
            archive_path = record[3]
            full_path = os.path.join(VIDEO_DIR, archive_path[1:])
            try:
                fs = os.stat(full_path).st_size
            except FileNotFoundError:
                fs = 0

            result.append({
                'start': record[0],
                'end': record[1],
                'date': record[2],
                'archivePostfix': archive_path,
                'cam': record[4],
                'id': record[5],
                'fileSize': fs
            })

        return result


def save_supervisor_config():
    with open(SUPERVISOR_CAMERAS_CONF, 'w') as f:
        config.write(f)
    print('launching update...')
    res = os.system('supervisorctl update')
    print('update fail' if res else 'update success', flush=True)

class Thumb(Resource):
    def get(self, cam_id, time):
        print(cam_id, time, flush=True)
        date = datetime.datetime.fromtimestamp(time)
        j_day = int(julian.to_jd(date))
        ms = (date.hour*60*60 + date.minute*60 + date.second) * 1000
        print(j_day, ms, flush=True)
        conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
        cur = conn.cursor()
        cur.execute("select heatmap from records where date=%s and start_time >= %s and cam='cam%s' limit 1;" % (j_day, ms, cam_id))
        img = base64.b64decode(cur.fetchone()[0])

        io_img = io.BytesIO(img)
        pil_img = Image.open(io_img)
        res_img = pil_img.resize((175,100))
        out_img = io.BytesIO()
        res_img.save(out_img, format='PNG')

        response = make_response(out_img.getvalue())
        response.headers.set('Content-Type', 'image/png')
        response.headers.set('Content-Disposition', 'inline', filename='thumb.png')
        return response

lock = Lock()

app = Flask(__name__)
#app=CORS(app)

api = Api(app)
#api = CORS(api)
api.add_resource(Cam, '/')
api.add_resource(Stat_fs, '/stat_fs')
api.add_resource(Stat, '/stat', endpoint='events_stat')
api.add_resource(ArchiveEvents, '/archive', endpoint='events_archive')
api.add_resource(ArchiveVideo, '/archive_video', endpoint='video_archive')
api.add_resource(DatabaseData, '/db/<string:data>', endpoint='db_data')
api.add_resource(DatabaseEventsData, '/archivedb/<string:data>', endpoint='db_arhcive_data')
api.add_resource(Thumb, '/thumb/<int:cam_id>/<int:time>/')

app.config.update(
    CELERY_BROKER_URL='amqp://teorema:teorema@0.0.0.0:5672//',
    CELERY_RESULT_BACKEND='amqp://teorema:teorema@0.0.0.0:5672//'
)



@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
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
def delete_path(self, path):
    shutil.rmtree(path)
    print('Camera successfully deleted')


config = configparser.ConfigParser()

print('testing permissions to supervisor...')
try:
    config.read(SUPERVISOR_CAMERAS_CONF)
    save_supervisor_config()
    if os.system('supervisorctl status > /dev/null') != 0:
        raise Exception('Cannot run supervisorctl')
except:
    print(SUPERVISOR_ERROR_TEXT)
    raise
print('permissions ok')
print('found %s cameras' % len(config.sections()))


