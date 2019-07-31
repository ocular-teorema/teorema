import os
import datetime
from deleter.lib.file_size import return_name,create_name_path,find_files_older,return_name,convert_name_to_datetime


def day_limit():
    today = datetime.datetime.now()
    hour = datetime.timedelta(days=1)
    limit = today - hour
    delay = limit.replace(second = 0,microsecond=0)
    return delay


def create_pairs(file):
    name = return_name(file)
    date_create = convert_name_to_datetime(name)
    name_path = create_name_path(date_create,file)
    return name_path




def sort_pairs_by_date(pairs):
    pairs_for_sort = pairs
    data_sorted = sorted(pairs_for_sort, key=lambda item: list(item.keys()))
    return data_sorted




def find_older(video_file):
    delay = day_limit()
    name = return_name(video_file)
    name_path = create_name_path(name,video_file)
    older_video = find_files_older(name_path,delay)
    return older_video
