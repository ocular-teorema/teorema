import os
import heapq
import re
import configparser
import datetime
import psycopg2
import datetime
import julian

config = configparser.ConfigParser()
PROCESS_DIR = '/home/_processInstances'
VIDEO_DIR = '/home/_VideoArchive'
GAP = 2


def delvideo():
    conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
    cur = conn.cursor()
    for subdirname in os.listdir(PROCESS_DIR):
        if not subdirname.startswith('cam'):
            continue
        dirname = os.path.join(PROCESS_DIR, subdirname)
        if not os.path.isdir(dirname):
            continue
        print('work on %s' % dirname, 'at', str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19])

        os_storage = os.statvfs(VIDEO_DIR)
        storage_free = os_storage.f_bavail * os_storage.f_frsize
        path_info = parse_fs(dirname)
        du_limit = path_info['disk_usage']
        # fp_oldest = path_info['oldest_four'][0]

        if storage_free < du_limit:
            print('free storage is %s' % storage_free, 'at', str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19])
            space_to_free = du_limit - storage_free
            f_count = calc_amount_to_delete(dirname, space_to_free)
            f_paths = find_oldest(dirname, f_count)
            print('will be deleted %s files in  %s' % (f_count, dirname), 'at', str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19])
            for video in f_paths:
                try:
                    os.remove(video)
                except Exception as e:
                    print('cannot remove %s due to %s', (video, e))
                    continue

        try:
            config.read(os.path.join(dirname, 'theorem.conf'), encoding='utf-8')
            storage_life = int(config['PipelineParams']['storage_life'])
        except Exception as e:
            print('error %s while reading %s conf' % (e, dirname))
            continue

        if storage_life == 0:
            continue

        print('removing too old db records/events at', str(datetime.datetime.isoformat(datetime.datetime.now(), sep='_'))[:19])

        limit = int(julian.to_jd(datetime.datetime.now() - datetime.timedelta(days=storage_life + GAP)))
        print('deleting from events at {}, can take a while'.format(str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19]))
        cur.execute("delete from events where archive_file1 like '/%s%%' and date < %s;" % (subdirname, limit))
        conn.commit()
        print('deleting from records at {}, can take a while'.format(str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19]))
        cur.execute("delete from records where video_archive like '/%s%%' and date < %s;" % (subdirname, limit))
        conn.commit()
        print('removing old files with related db records/events at', str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19])

        videodirname = os.path.join(VIDEO_DIR, subdirname)
        try:
            os.stat(videodirname)
        except Exception as e:
            print('ignoring %s due to %s' % (videodirname, e))
            continue
        for fname in os.listdir(videodirname):
            if not fname.endswith('mp4'):
                continue
            fpath = os.path.join(videodirname, fname)
            now = datetime.datetime.now()
            fdate = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))

            if (now - fdate).days <= storage_life:
                continue

            print('removing', fpath, 'at', str(datetime.datetime.isoformat(datetime.datetime.now(),sep='_'))[:19])
            try:
                os.remove(fpath)
            except Exception as e:
                print('cannot remove %s due to %s', (fpath, e))
                continue
            bd_filename = os.path.join('/', subdirname, fname)
            cur.execute("delete from records where video_archive='%s';" % bd_filename)
            cur.execute(
                "delete from events where archive_file1='%s' or archive_file2='%s';" % (bd_filename, bd_filename))
            conn.commit()


def usage_for_list(video_list):
    return sum(os.stat(vid).st_size for vid in video_list)


def parse_fs(videodirpath):
    oldest_four = find_oldest(videodirpath, 4)
    fusage = usage_for_list(oldest_four) * 6
    return {
        'disk_usage': fusage,
        'oldest_four': oldest_four
    }


def find_oldest(workpath, count=1):
    return heapq.nsmallest(count,
                           (os.path.join(dirname, filename)
                            for dirname, dirnames, filenames in os.walk(workpath)
                            for filename in filenames
                            if filename.endswith('.mp4')),
                           key=lambda fn: os.stat(fn).st_mtime
                           )


def convert_name_to_datetime(name):
    pattern = r'\w{1,3}\d{1,3}_\d\d_\d\d_\d{4}___\d\d_\d\d_\d\d'
    if re.match(pattern, name) is not None:
        if name is not None:
            w_ext = name.split('_')
            dt = datetime.datetime(int(w_ext[3]), int(w_ext[2]), int(w_ext[1]))
            tm = datetime.time(int(w_ext[6]), int(w_ext[7]), int(w_ext[8]))
            time_creation = dt.combine(dt, tm)
            return time_creation


def calc_amount_to_delete(workpath, space):
    # videodirpath = os.path.join(VIDEO_DIR, workpath)
    files_count = len(os.listdir(workpath))
    for f_amount in range(1, files_count + 1):
        files = find_oldest(workpath, f_amount)
        filesizes = usage_for_list(files)
        if filesizes >= space:
            return f_amount


if __name__ == '__main__':
    delvideo()
