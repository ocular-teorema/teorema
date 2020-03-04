import os
from datetime import datetime
import psycopg2


# module has function for delete with specific conditions

def delete_file(filename):
    os.remove(filename)


def find_free_space():
    # values on some machine possible some devert
    # free size in bites
    st = os.statvfs('/home/_VideoArchive')
    free = st.f_bavail * st.f_frsize
    return free


def delete_handler(files, limit, middle_file, ratio, free_space=1, ):
    # count how many files need deleted
    conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
    cur = conn.cursor()
    counter = 0
    delete_paths = [i['path'] for i in files]
    print(str(len(files)) + ' files for delete', 'at', str(datetime.isoformat(datetime.now(), sep='_'))[:19],
          flush=True)
    free_space = find_free_space()
    try:
        while free_space < limit:
            free_space = find_free_space()
            delete_file(delete_paths[counter])
            video = '/' + '/'.join(delete_paths[counter].split('/')[3:])
            cur.execute("delete from records where video_archive=%s;", (video, ))
            cur.execute("delete from events where archive_file1=%s or archive_file2=%s;", (video, video))
            conn.commit()
            print('success deleted', delete_paths[counter], flush=True)
            counter += 1
        else:
            conn.close()
            print("you have enough space " + str(free_space / ratio) + 'gb', 'at',
                  str(datetime.isoformat(datetime.now(), sep='_'))[:19], flush=True)
            print('*' * 50, flush=True)
            print(counter, 'files deleted at', str(datetime.isoformat(datetime.now(), sep='_'))[:19],
                  flush=True)
    except Exception as err:
        conn.close()
        print('error in deleting, message: {}'.format(str(err)), flush=True)
        print('*' * 50, flush=True)
        print(counter, 'files deleted at', str(datetime.isoformat(datetime.now(), sep='_'))[:19],
              flush=True)
