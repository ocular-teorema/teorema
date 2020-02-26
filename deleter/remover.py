import os
import re
from deleter.lib.file_size import find_size
from deleter.lib.delete_handler import find_free_space, delete_handler
import datetime
import configparser


# bite
ratio = 1000000000
# basic file weigth file in directory
middle_file = 100 * ratio

config = configparser.ConfigParser()
VIDEO_DIR = '/home/_VideoArchive'
PROCESS_DIR = '/home/_processInstances'


def deleter_main():
    # each func must me for single and call with map)
    videos = find_all_files(VIDEO_DIR)
    if videos == []:
        print('no videos', flush=True)
        return
    # return list


    files_by_hour = map(find_size, [i['path'] for i in videos])
    total_by_hour = (sum(filter(None, files_by_hour)))
    print('size files by hour' + str(total_by_hour / ratio) + "gb", 'at',
          str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19], flush=True)
    # return value
    limit_for_delete = total_by_hour * 7
    print('limit today is' + str(limit_for_delete / ratio) + 'gb', 'at',
          str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19], flush=True)


    sorted_videos = sort_by_storage(videos)

    free_space = find_free_space()
    print('free is' + str(free_space / ratio) + 'gb', 'at',
          str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19], flush=True)

    delete_handler(sorted_videos, limit_for_delete, middle_file, ratio)


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


def find_all_files(_PATH):
    files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(_PATH):
        for file in f:
            if re.match(r'\w{1,3}.{1,30}_\d\d_\d\d_\d{4}___\d\d_\d\d_\d\d.mp4', file):
                camera_name = r.split('/')[-1]
                files.append({'path': os.path.join(r, file),
                              'storage_days': get_storage_value(camera_name),
                              'record_date': get_video_date(file)})
    return files


def get_video_date(video):
    video_name = video[:-4]
    date = {
        'day': video_name.split('_')[3],
        'month': video_name.split('_')[4],
        'year': video_name.split('_')[5],
        'hour': video_name.split('_')[8],
        'minute': video_name.split('_')[9],
        'second': video_name.split('_')[10]
    }
    return datetime.datetime(**date)
