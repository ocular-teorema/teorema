import os
import configparser
import datetime
import psycopg2
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
        print('work on %s' % dirname)
        try:
            config.read(os.path.join(dirname, 'theorem.conf'), encoding='utf-8')
            storage_life = int(config['PipelineParams']['storage_life'])
        except Exception as e:
            print('error %s while reading %s conf' % (e, dirname))
            continue
        if storage_life == 0:
            continue
        
        print('removing too old db records/events')
        
        limit = int(julian.to_jd(datetime.datetime.now() - datetime.timedelta(days=storage_life+GAP)))
        print('deleting from events, can take a while')
#        cur.execute("delete from events where archive_file1 like '/%s%%' and date < %s;" % (subdirname, limit))
        conn.commit()
        print('deleting from records, can take a while')
#        cur.execute("delete from records where video_archive like '/%s%%' and date < %s;" % (subdirname, limit))
        conn.commit()
        print('removing old files with related db records/events')

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
            if (now-fdate).days <= storage_life:
                continue

            print('removing', fpath)
            try:
                os.remove(fpath)
            except Exception as e:
                print('cannot remove %s due to %s', (fpath, e))
                continue
            bd_filename = os.path.join('/', subdirname, fname)
            cur.execute("delete from records where video_archive='%s';" % bd_filename)
            cur.execute("delete from events where archive_file1='%s' or archive_file2='%s';" % (bd_filename, bd_filename))
            conn.commit()

if __name__ == '__main__':
    delvideo()
