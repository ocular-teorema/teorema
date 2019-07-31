import os
from deleter.lib.search_videos import find_videos
from deleter.lib.file_size import find_size
from deleter.lib.older_by import find_older,sort_pairs_by_date,create_pairs
from deleter.lib.delete_handler import find_free_space,delete_handler
from delvideo import VIDEO_DIR

#_PATH = os.getcwd()
#_PATH = '/home/_VideoArchive'
#bite
ratio = 1000000000
#basic file weigth file in directory
middle_file = 40*ratio




def deleter_main():
    #each func must me for single and call with map)
    #return list
    videos = find_videos(VIDEO_DIR)
    #return list
    files_by_hour = map(find_size,videos)
    total_by_hour = (sum(filter(None,files_by_hour)))
    print('size files by hour'+str(total_by_hour/ratio)+"gb")
    #return value
    limit_for_delete = total_by_hour*4
    print('limit today is'+str(limit_for_delete/ratio )+'gb')
    #return list
    older_files = filter(None,map(find_older,videos))
    older_files_by_date =filter(None, map(create_pairs,older_files))
    #create list with most older files
    files_for_delete = sort_pairs_by_date(older_files_by_date)
    #print(list(older_files_by_date))
    free_space = find_free_space()
    print('free is' + str(free_space/ratio)+'gb')
    #default free_space is 0 for delete all
    #func take inside list with files

    delete_handler(files_for_delete,limit_for_delete,middle_file,ratio)


