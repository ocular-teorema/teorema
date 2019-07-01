from delvideo_addition import find_size
from delvideo_addition import search_videos
from delvideo_addition import find_free_space,delete_by_free_space


def delvideo_addition_main():
    files = search_videos()
    videos_none = filter(None,files)
    files_by_hour = map(find_size,files)
    total_by_hour = sum(filter(None,files_by_hour))
    limit = (total_by_hour*4)/1000000
    print(limit)
    print(find_free_space())
    free_space = find_free_space()
    delete_by_free_space(limit,free_space)

#if __name__ == "__main__":
#    main()

