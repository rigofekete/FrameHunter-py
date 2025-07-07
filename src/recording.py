import subprocess
import av
import numpy as np
import os
import fractions
import time
import win32gui
import ctypes
import datetime

# COMMAND TO RUN FFMPEG FROM WINDOWS, WITH MAX COMPATIBILITY, FOR 15 SECONDS 

# ffmpeg.exe -f gdigrab -framerate 30 -i desktop -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p -profile:v baseline -level 3.0 -t 15 output.mp4

# COMMAND TO RUN FFMPEG USING NVIDIA GPU AS THE CAPTURE SOURCE (ddagrab) FOR PROPER QUALITY AND FPS RECORDING

# >ffmpeg -f lavfi -i "ddagrab=framerate=60" -c:v h264_nvenc -cq 18 -y output.mp4


# Set the FFmpeg path

# os.environ['FFMPEG_BINARY'] = """
# /mnt/c/Users/fabri/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-7.1-full_build/bin/ffmpeg.exe
# """.strip()
#


# def get_window_rect(window_title):
#     hwnd = win32gui.FindWindow(None, window_title)
#     if hwnd:
#         return win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
#     return None
#

def get_dpi_aware_window_rect(title):
    hwnd = win32gui.FindWindow(None, title)
    if not hwnd:
        print("Window not found")
        return None

    win32gui.ShowWindow(hwnd, 1)
    win32gui.SetForegroundWindow(hwnd)
    
    # Get window rect (in physical pixels)
    rect = win32gui.GetWindowRect(hwnd)
    x, y, r, b = rect
    width = r - x
    height = b - y

    # Get DPI for the window using Windows API
    try:
        # Windows 10+ (1607+) method
        user32 = ctypes.windll.user32
        dpi = user32.GetDpiForWindow(hwnd)
    except AttributeError:
        print("user32 and dpi value returns with ctypes failed")
        # Fallback to standard DPI


    #### DPI SCALE CALCULATION
    # scale = dpi / 96.0: Calculates the DPI scaling factor. Since 96 DPI is the Windows standard baseline:
    # 96 DPI = 1.0 scale (100% scaling)
    # 120 DPI = 1.25 scale (125% scaling)
    # 144 DPI = 1.5 scale (150% scaling)
    # 192 DPI = 2.0 scale (200% scaling)

    scale = dpi / 96.0


    x = int(x * scale) + 10             # add/sub values to fine-tune capturing x, y, w, h regions
    y = int(y * scale) + 20             # add/sub values to fine-tune capturing x, y, w, h regions
    width = int(width * scale) - 20     # add/sub values to fine-tune capturing x, y, w, h regions
    height = int(height * scale) -20    # add/sub values to fine-tune capturing x, y, w, h regions

    # we need to make sure that the w and h values are even! 
    # (libx264 requires width/height divisible by 2)
    width = width - (width % 2)
    height = height - (height % 2)
    return (x, y, x + width, y + height)

class ScreenRecorder:
    def __init__(self):
        self.input_container = None
        self.output_container = None
        self.output_stream = None
        self.input_stream = None
        self.recording = False
        self.previous_frame = None


    def capture_frames(self):
        # window_title ="Pro Evolution Soccer 2" 
        # window_title ="desktop" 

        # Apparently certain window hwnd's like these 2 ones below seem to have restrictions for capture
        # and restore (ShowWindow() function for example), need to investigate this further
        # rect = get_dpi_aware_window_rect("Calculator")
        # rect = get_dpi_aware_window_rect("Steam")

        rect = get_dpi_aware_window_rect("PCSX2 v2.2.0")
        # rect = get_dpi_aware_window_rect("Pro Evolution Soccer 2")
        # rect = get_dpi_aware_window_rect("WE6FE Classicos 2.0 (Hack Ed)")
        if rect:
            print(f"Calculating rect....")
            x, y, right, bottom = rect
            width =  right - x
            height = bottom - y
            print(f"width {width} height {height}")
        else:
            print("rect is null")

        video_size = f'{width}x{height}'

        self.input_container = av.open('desktop',
                                        format='gdigrab',
                                        mode='r',
                                        options={
                                            'framerate': '30',
                                            'offset_x': str(x),
                                            'offset_y': str(y),
                                            # 'video_size': video_size,  
                                            # 'video_size': '1920x1080',  
                                            'video_size': f'{width}x{height}',  
                                            'show_region': '0',
                                            # 'draw_mouse': '0',
                                        }
                                )


    def start_recording(self):
        if not self.recording:
            try:
                now = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-')
                output_path = os.path.abspath(f'output\\{now}.mp4')
                self.output_container = av.open(output_path, 'w')

                self.output_stream = self.output_container.add_stream('libx264', rate=30)
                self.output_stream.width = self.input_container.streams.video[0].width
                self.output_stream.height = self.input_container.streams.video[0].height
                self.output_stream.pix_fmt = 'yuv420p'
                # self.output_stream.codec_context.time_base = fractions.Fraction(1, 30)
                # self.output_stream.time_base = fractions.Fraction(1, 60)
                self.output_stream.codec_context.options = {
                    # 'rc': 'cbr',
                    # 'bitrate': '5000k'
                    # 'level': '3.0',
                    # 'preset': 'medium',        # Changed from 'ultrafast' - better quality
                    # 'tune': 'zerolatency',     # Keep for real-time
                    # 'crf': '18',               # Much lower CRF = higher quality (was 23)
                    # 'profile': 'high',         # Changed from 'baseline' - better compression
                    # 'level': '4.0',            # Higher level for better features
                    # 'threads': '4',
                    # 'thread_type': 'slice',
                    # 'bf': '3',                 # B-frames for better compression
                    # 'refs': '3',               # Reference frames for quality
                    # 'me_method': 'hex',        # Better motion estimation
                    # 'subq': '7',               # Higher subpixel motion estimation
                    # 'trellis': '1',            # Quantization optimization
                    # 'fast_pskip': '1',         # Skip optimization
                    # 'mixed_refs': '1',         # Mixed reference frames
                    # 'weightb': '1',            # Weighted B-frames
                    # 'aq_mode': '1',            # Adaptive quantization
                    # 'aq_strength': '1.0'       # AQ strength
                }

                self.recording = True
                print("Recording started")
                return True

            except Exception as e:
                print(f"Failed to start recording: {e}")
                import traceback
                traceback.print_exc()
                return False


    def stop_recording(self):
        if self.recording:
            self.output_container.close()
            self.recording = False



    def process_frames(self):
        if not self.recording:
            self.start_recording()
        
        time_base = fractions.Fraction(1, 30)
        self.output_stream.time_base = time_base

        start_time = time.time()
        last_pts = -1

        frame_index = 0 

        try:
            while self.recording:
                try:
                    for frame in self.input_container.decode(video=0):
                        now = time.time()
                        elapsed_time = now - start_time

                        current_pts = int(elapsed_time / float(time_base))  
                        # print(f"ELAPSED TIME: {elapsed_time} == CURRENT PTS: {current_pts}")

                        if current_pts <= last_pts:
                            continue

                        frame.pts = current_pts 
                        frame.time_base = time_base

                        packet = self.output_stream.encode(frame)

                        self.output_container.mux(packet)

                        last_pts = current_pts 

                except av.BlockingIOError:
                    pass
        except KeyboardInterrupt:
            print("Recording stopped by user")

        packet = self.output_stream.encode(None)
        self.output_container.mux(packet)

        self.input_container.close()
        self.output_container.close()

    # def process_frames(self):
    #     frame_count = 0
    #     duration = 90
    #     for frame in self.input_container.decode():
    #         print(frame)
    #         img_array = frame.to_ndarray(format='bgr24')
    #
    #         if self.detect_changes(img_array):
    #             if not self.recording:
    #                 self.start_recording()
    #                 print("Change detected. Start recording")
    #         else:
    #             if self.recording:
    #                 self.stop_recording()
    #                 print("Pattern matched. Stop recording")
    #
    #         if self.recording:
    #             # frame_yuv = frame.reformat(format='yuv420p')
    #             # packet = self.output_stream.encode(frame_yuv)
    #             # self.output_container.mux(packet)
    #
    #             # Reformat frame
    #             frame_yuv = frame.reformat(format='yuv420p')
    #
    #             # Resize frame to match output stream dimensions (200x200)
    #             frame_yuv = frame_yuv.reformat(width=self.input_stream.width, height=self.input_stream.height)
    #
    #             # Set timestamp (important for proper playback)
    #             # frame_yuv.pts = None
    #             # # TODO: for now we reset the playback timestamp. Check this after we start adding
    #             # # more capture frames and not only 1 as current
    #             # frame_yuv.pts = 0
    #
    #             # frame.pts = 0
    #
    #             # Encode returns multiple packets - iterate over them
    #             for packet in self.output_stream.encode(frame_yuv):
    #                 print(f"packet: {packet}")
    #
    #                 if packet.dts is None:
    #                     continue
    #
    #                 self.output_container.mux(packet)
    #         frame_count += 1
    #         if frame_count >= duration:
    #             break
    #
    #     self.output_container.close()
    #     self.input_container.close()
    #     # self.previous_frame = img_array
    #
    #
    def detect_changes(self, current_frame):
        if self.previous_frame is None:
            return False

        diff = np.sum(np.abs(current_frame - self.previous_frame))
        return diff > 1000
    
