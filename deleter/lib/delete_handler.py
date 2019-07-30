import os

#module has function for delete with specific conditions

def delete_file(filename):
    os.remove(filename)

def find_free_space():
    #values on some machine possible some devert
    #free size in bites
    st = os.statvfs('/')
    free = st.f_bavail * st.f_frsize
    return free


def delete_handler(files, limit,middle_file,ratio,free_space = 0,):
    # count how many files need deleted
    quantity_for_delete = abs(int(round((limit* ratio - free_space) / middle_file)))
    print('lim is '+str(limit/rations)+' mb')
    print(free_space)
    print('files need deleted '+str(quantity_for_delete))
    try:
        for i in range(quantity_for_delete):
            #delete_file(files[i])
            print(str(files[i]) + ' file will be deleted')
    except:
        print(str(quantity_for_delete)+'will deleted')
        pass
