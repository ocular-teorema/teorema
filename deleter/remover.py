import os
from deleter.lib.search_videos import find_videos
from deleter.lib.file_size import find_size
from deleter.lib.older_by import find_older,sort_pairs_by_date,create_pairs
from deleter.lib.delete_handler import find_free_space,delete_handler
from delvideo import VIDEO_DIR

#_PATH = os.getcwd()
#_PATH =
#bite
ratio = 1048576
#basic file weigth file in directory
middle_file = 40*ratio




def main():
    #each func must me for single and call with map)
    #return list
    videos = find_videos(VIDEO_DIR)
    #return list
    files_by_hour = map(find_size,videos)
    #return value
    total_by_hour = sum(files_by_hour)
    #return value
    limit_for_delete = total_by_hour*3
    #return list
    older_files = map(find_older,videos)
    older_files_by_date = map(create_pairs,older_files)
    #create list with most older files
    files_for_delete = sort_pairs_by_date(older_files_by_date)
    free_space = find_free_space()
    print(files_for_delete)
    #default free_space is 0 for delete all
    #func take inside list with files
    print(older_files)
    delete_handler(older_files,limit_for_delete,middle_file,ratio)

if __name__ == "__main__":
    main()
