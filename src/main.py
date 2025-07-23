import os
import sys
from os import system
from recording import ScreenRecorder
from merge_files import merge_files
from global_vars import MENU_TXT, SUCCESS, ERROR

SOURCE = "output"

def main():

    while(True):

        system('cls')
        print(MENU_TXT)
        choice = input()
        buffer = 0
        fps = 0

        system('cls')

        # Default capture
        if choice == '1':
            recorder = ScreenRecorder()
            recorder.capture_frames()
            recorder.process_frames()
            input('\npress any key to enter menu....')
        # Custom capture
        elif choice == '2':
            buffer = int(input('Buffer: '))
            fps = int(input('FPS: '))
            recorder = ScreenRecorder(buffer_seconds=buffer, fps=fps)
            recorder.capture_frames()
            recorder.process_frames()
            input('\npress any key to enter menu....')
        # Merge files
        elif choice == '3':
            try:
                if merge_files(SOURCE):
                    print(f'{SUCCESS} Files merged successfully!')
            except Exception as e:
                print(f'{ERROR} Error merging or deleting files: {e}')
            input('\npress any key to enter menu....')
        # Exit
        elif choice == '4':
            system('cls')
            sys.exit(1)

        system('cls')

if __name__ == "__main__":
    main()
