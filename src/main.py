import os
# import pathlib
from recording import ScreenRecorder

def main():
        
    recorder = ScreenRecorder()

    while(True):
        recorder.capture_frames()
    

    


if __name__ == "__main__":
    main()
