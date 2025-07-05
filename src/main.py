import os
# import pathlib
from recording import ScreenRecorder

def main():
        
    recorder = ScreenRecorder()
    recorder.capture_frames()
    recorder.process_frames()

    # while(True):
    #     recorder.capture_frames()
    #     recorder.process_frames()
    

    


if __name__ == "__main__":
    main()
