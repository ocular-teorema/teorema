import datetime
import os
import re

def create_limit():
  today = datetime.datetime.now()
  hour = datetime.timedelta(hours=1)
  limit = today - hour
  delay = limit.replace(second = 0,microsecond=0)
  return delay

def return_name(path):
  filename = os.path.splitext(path)[0]
  name = filename.split('/')[-1]
  return name

def create_name_path(name, path):
  name_path = {name:path}
  return name_path

def find_files_older(name_path,time_limit):
      for name, path in name_path.items():
          time_creation = convert_name_to_datetime(name)
          if time_creation <= time_limit:
              return path
          else:
              continue


def convert_name_to_datetime(name):
    pattern = r'\w{1,3}\d{1,3}_\d\d_\d\d_\d{4}___\d\d_\d\d_\d\d'
    if (re.match(pattern,name) is not None):
            if name is not None:
                w_ext = name.split('_')
                dt = datetime.datetime(int(w_ext[3]),int(w_ext[2]),int(w_ext[1]))
                tm = datetime.time(int(w_ext[6]),int(w_ext[7]),int(w_ext[8]))
                time_creation = dt.combine(dt, tm)
                return time_creation


def find_weight(path_to_file):
  if path_to_file is not None:
      statinfo = os.stat(path_to_file)
      size = statinfo.st_size
      return size



def find_size(filename):
  time_limit = create_limit()
  name = return_name(filename)
  name_path = create_name_path(name, filename)
  file_older_one_hour = find_files_older(name_path,time_limit)
  weight = find_weight(file_older_one_hour)
  return weight
