import os
from recording import ScreenRecorder

def main():
        
    recorder = ScreenRecorder(buffer_seconds=8, fps=30)
    recorder.capture_frames()
    recorder.process_frames()

if __name__ == "__main__":
    main()
