# import os
import sys
from os import system
from main_helper import def_cap, custom_cap, live_full, live_crop, merge
from global_vars import MENU_TXT

def main():

    while(True):
        system('cls')
        print(MENU_TXT)
        choice = input()
        system('cls')

        # Default capture
        if choice == '1':
            def_cap()

        # Custom capture
        elif choice == '2':
            custom_cap()

        # Live recording fullscreen
        elif choice == '3':
            live_full()

        # Live recording crop
        elif choice == '4':
            live_crop()

        # Merge files
        elif choice == '5':
            merge_files()

        # Exit
        elif choice == '6':
            print('Szia!')
            input()
            system('cls')
            sys.exit(1)

        # system('cls')

if __name__ == "__main__":
    main()
