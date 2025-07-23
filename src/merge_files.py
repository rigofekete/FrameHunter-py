import ffmpeg
import os
import sys

OUTPUT_PATH = "merged_videos"

SUCCESS = "✅"
ERROR = "❌"
WARNING = "⚠️"
INFO = "ℹ️"
DEBUG = "🔍"
START = "🚀"
STOP = "🛑"

def merge_files(source):

    files = os.listdir(source)
    files_sum = len(files)

    if not files_sum % 2 == 0:
        print(f'{ERROR} Total ouput files should be even. Current number of files: {files_sum}')
        print(f'{ERROR} Terminating merger...')
        return False

    if not files_sum:
        print(f'{ERROR} No files to merge. Current number of files: {files_sum}')
        print(f'{ERROR} Terminating merger...')
        return False 

    list_index = 0
    file_index = 1
    append_count = 0
    input_files = [None for i in range(files_sum)]

    for file in files:
        # print(f'Printing current file: {file}\n')
        if file.startswith(f'{file_index}-live'):
            # print('adding live\n')
            input_files[list_index + 1] = ffmpeg.input(f'{source}\\{file}')
            # input_files[list_index + 1] = file
            append_count += 1
        elif file.startswith(f'{file_index}-pre'):
            # print('adding pre\n')
            # input_files[list_index]  = file
            input_files[list_index]  = ffmpeg.input(f'{source}\\{file}')

            append_count += 1
        # print(input_files)

        if append_count % 2 == 0:
            list_index += 2
            file_index += 1

    print(f'{START} Processing and merging input streams......')
    print(input_files)

    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH) 

    ffmpeg.concat(*input_files, v=1).output(f'{OUTPUT_PATH }\\final{files[0][-10:-4]}.mp4').run()

    print(f'{START} Deleting video parts from the {OUTPUT_PATH} folder')
    for f in os.listdir(source):
        os.remove(f'{source}\\{f}')

    return True


