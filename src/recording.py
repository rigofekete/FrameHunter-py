import subprocess
import av
import numpy as np
import os

# COMMAND TO RUN FFMPEG FROM WINDOWS, WITH MAX COMPATIBILITY, FOR 15 SECONDS 
# ffmpeg.exe -f gdigrab -framerate 30 -i desktop -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p -profile:v baseline -level 3.0 -t 15 output.mp4


# Set the FFmpeg path
# os.environ['FFMPEG_BINARY'] = """
# /mnt/c/Users/fabri/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-7.1-full_build/bin/ffmpeg.exe
# """.strip()



class ScreenRecorder:
    def __inti__(self):
        self.input_container = None
        self.output_container = None
        self.output_stream = None
        self.recording = False
        self.previous_frame = None


    def capture_frames(self):
        self.input_container = av.open('desktop', 
                                        format='gdigrab',
                                        options={
                                            'offset_x': '100',
                                            'offset_y': '100',
                                            'video_size': '200x200'
                                        }
                                )
        print("BOOOM")

    
    def start_recording(self):
        if not self.recording:
            self.output_container = av.open('../videos/output.mp4', mode='w')
            self.output_stream = self.output_container.add_stream('libx264', rate=30)
            self.output_stream.width = 200
            self.output_stream.height = 200
            self.output_stream.pix_fmt = 'yuv420p'
            self.recording = True

    def stop_recording(self):
        if self.recording:
            self.output_container.close()
            self.recording = False

    def process_frames(self):
        for frame in self.input_container.decode():
            img_array = frame.to_ndarray(format='bgr24')

            if self.detect_changes(img_array):
                if not self.recording:
                    self.start_recording()
                    print("Change detected. Start recording")
            else:
                if self.recording:
                    self.stop_recording()
                    print("Pattern matched. Stop recording")

            if self.recording:
                frame_yuv = frame.reformat(format='yuv420p')
                packet = self.output_stream.encode(frame_yuv)
                self.output_container.mux(packet)

        self.previous_frame = img_array


    def detect_changes(self, current_frame):
        if self.previous_frame is None:
            return False

        diff = np.sum(np.abs(current_frame - self.previous_frame))
        return diff > 1000
    
