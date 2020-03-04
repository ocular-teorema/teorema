import os
from datetime import datetime
import psycopg2


# module has function for delete with specific conditions

def delete_file(filename):
    os.remove(filename)


def find_free_space(all_directories):
    # values on some machine possible some devert
    # free size in bites
    st = os.statvfs('/home/_VideoArchive')
    free = st.f_bavail * st.f_frsize
    return free


def delete_handler(files, limit, middle_file, ratio, all_directories, free_space=1, ):
    # count how many files need deleted
    conn = psycopg2.connect(host='localhost', dbname='video_analytics', user='va', password='theorema')
    cur = conn.cursor()
    counter = 0
    # delete_paths = [i['path'] for i in files]
    delete_paths = files
    print(str(len(files)) + ' files for delete', 'at', str(datetime.isoformat(datetime.now(), sep='_'))[:19],
          flush=True)
    free_space = find_free_space(all_directories)
    try:
        while free_space < limit:
            free_space = find_free_space(all_directories)
            delete_file(delete_paths[counter]['path'])
            video = delete_paths[counter]['path'].split(delete_paths[counter]['root_path'])[-1]
            cur.execute("delete from records where video_archive=%s;", (video,))
            # cur.execute("select file_offset_sec from events where archive_file1=%s or archive_file2=%s;",
            #             (video, video))
            # for event in cur.fetchall():
            #     event_file = os.path.join('/'.join(delete_paths[counter]['path'].split('/')[:-1]), 'alertFragments',
            #                        'alert' + str(event[0]) + '.mp4')
            #     if os.path.isfile(event_file):
            #         delete_file(event_file)
            #         print(event_file, 'event deleted', flush=True)
            cur.execute("delete from events where archive_file1=%s or archive_file2=%s;", (video, video))
            conn.commit()
            print('success deleted', delete_paths[counter]['path'], flush=True)
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
