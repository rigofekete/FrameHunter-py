from os import system
from recording import ScreenRecorder
from merge_files import merge_files
from global_vars import (
        MENU_TXT, WIN_TXT, MODE_TXT,
        LIVE, FULL,
        SUCCESS, ERROR, WARNING, START,
        PES2, WE6, DAZN1_VLC 
)

SOURCE = "output"

def switch(window):
    if window == 1:
        return PES2
    elif window == 2:
        return WE6
    elif window == 3:
        return DAZN1_VLC
    else:
        print('Invalid option')
        return None

def def_cap():
    recorder = ScreenRecorder()
    recorder.capture_frames()
    recorder.process_frames()
    input('\npress any key to enter menu....')

def custom_cap():
    option = int(input(f'{WIN_TXT} \n>>'))
    option = switch(option)
    system('cls')

    mode = int(input(f'{MODE_TXT} \n>>'))
    system('cls')
    buffer = int(input('Buffer: '))
    fps = int(input('FPS: '))

    recorder = ScreenRecorder(window=option, mode=mode, buffer_seconds=buffer, fps=fps)
    recorder.capture_frames()
    recorder.process_frames()
    input('\npress any key to enter menu....')


def live_full():
    choice = int(input(f'{WIN_TXT} \n>>'))
    choice = switch(choice)

    print('\nStarting live recording (fullscreen)....\n')
    recorder = ScreenRecorder(window=choice, mode=LIVE)
    if recorder.capture_frames():
        recorder.process_frames()
    input('\npress any key to enter menu....')

def live_crop():
    choice = int(input(f'{WIN_TXT} \n>>'))
    choice = switch(choice)

    print('\nStarting live recording (crop)....\n')
    recorder = ScreenRecorder(window=choice, mode=LIVE, crop='yes')
    if recorder.capture_frames():
        recorder.process_frames()
    input('\npress any key to enter menu....')


def merge():
    try:
        if merge_files(SOURCE):
            print(f'{SUCCESS} Files merged successfully!')
    except Exception as e:
        print(f'{ERROR} Error merging or deleting files: {e}')
    input('\npress any key to enter menu....')




