import os
from datetime import datetime


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
    counter = 0
    free_space = find_free_space()
    delete_paths = []
    for i in files:
        for key, value in i.items():
            delete_paths.append(value)
    print(str(len(files)) + ' files for delete', 'at', str(datetime.isoformat(datetime.now(), sep='_'))[:19], flush=True)
    free_space = find_free_space()
    try:
        while free_space < limit:
            free_space = find_free_space()
            delete_file(delete_paths[counter])
            counter += 1
            print(delete_paths[counter])
        else:
            print("you have enough space " + str(free_space / ratio) + 'gb', 'at',
                  str(datetime.isoformat(datetime.now(), sep='_'))[:19], flush=True)
    except:
        print('*' * 50)
        print('files' + str(counter) + 'deleted', 'at', str(datetime.isoformat(datetime.now(), sep='_'))[:19], flush=True)
        pass
