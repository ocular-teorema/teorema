import os
import re
from deleter.lib.file_size import find_size
from deleter.lib.delete_handler import find_free_space, delete_handler
import datetime
import configparser
import psycopg2
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django

django.setup()

from theorema.cameras.models import Camera

# bite
ratio = 1000000000
# basic file weigth file in directory
middle_file = 100 * ratio

config = configparser.ConfigParser()
VIDEO_DIR = '/home/_VideoArchive'
PROCESS_DIR = '/home/_processInstances'


def deleter_main():
    # each func must me for single and call with map)
    all_directories = list(Camera.objects.distinct('archive_path').values_list('archive_path', flat=True))
    videos = find_all_files(all_directories)
    if videos == []:
        print('no videos', flush=True)
        return
    # return list

    deleter_old(videos)

    files_by_hour = map(find_size, [i['path'] for i in videos])
    total_by_hour = (sum(filter(None, files_by_hour)))
    print('size files by hour' + str(total_by_hour / ratio) + "gb", 'at',
          str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19], flush=True)
    # return value
    limit_for_delete = total_by_hour * 7
    print('limit today is' + str(limit_for_delete / ratio) + 'gb', 'at',
          str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19], flush=True)

    sorted_videos = sort_by_storage(videos)

    free_space = find_free_space(all_directories)
    print('free is' + str(free_space / ratio) + 'gb', 'at',
          str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19], flush=True)

    delete_handler(sorted_videos, limit_for_delete, middle_file, ratio, all_directories)


def sort_by_storage(videos):
    return sorted(videos, key=lambda i: i['storage_days'] - (datetime.datetime.now() - i['record_date']).days)


def get_storage_value(camera_name):
    try:
        config.read(os.path.join(PROCESS_DIR, camera_name, 'theorem.conf'), encoding='utf-8')
        storage_life = int(config['PipelineParams']['storage_life'])
        return storage_life
    except Exception as e:
        print('error %s while reading %s conf' % (e, os.path.join(PROCESS_DIR, camera_name)))
        return 1000


def find_all_files(_PATHS):
    files = []
    # r=root, d=directories, f = files
    for _PATH in _PATHS:
        for r, d, f in os.walk(_PATH):
            for file in f:
                if re.match(r'\w{1,3}.{1,30}_\d\d_\d\d_\d{4}___\d\d_\d\d_\d\d.mp4', file):
                    camera_name = r.split('/')[-1]
                    files.append({'path': os.path.join(r, file),
                                  'root_path': _PATH,
                                  'storage_days': get_storage_value(camera_name),
                                  'record_date': get_video_date(file)})
    return files


def get_video_date(video):
    video_name = video[:-4]
    date = {
        'day': int(video_name.split('_')[3]),
        'month': int(video_name.split('_')[4]),
        'year': int(video_name.split('_')[5]),
        'hour': int(video_name.split('_')[8]),
        'minute': int(video_name.split('_')[9]),
        'second': int(video_name.split('_')[10])
    }
    return datetime.datetime(**date)


def deleter_old(videos):
    videos = [video['path'].split(video['root_path'])[-1] for video in videos]
    conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
    cur = conn.cursor()

    cur.execute('delete from records where video_archive not in %s;', (tuple(videos),))
    cur.execute('delete from events where archive_file1 not in %s or archive_file2 not in %s',
                (tuple(videos), tuple(videos)))
    conn.commit()
    conn.close()
