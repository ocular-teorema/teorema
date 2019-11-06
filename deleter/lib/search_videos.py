import os
import re



def find_all_files(_PATH):
    files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(_PATH):
        for file in f:
            if re.match(r'\w{1,3}.{1,29}_\d\d_\d\d_\d{4}___\d\d_\d\d_\d\d.mp4', file):
                files.append(os.path.join(r, file))
    return files



def find_videos(_PATH):
    video = find_all_files(_PATH)
    return video
