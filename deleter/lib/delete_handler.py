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


def delete_handler(files, limit,middle_file,ratio,free_space = 1,):
    # count how many files need deleted
    counter = 0
    free_space = find_free_space()
    while free_space< limit:
           free_space = find_free_space()
           delete_file(files[counter])
           print(counter)
           counter+1
           print(str(files[counter]) + ' file will be deleted')
