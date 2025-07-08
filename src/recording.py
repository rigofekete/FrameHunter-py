# probably will need this to run direct ffmpeg commands to generate high quality outputs 
import subprocess

import av
import numpy as np
import os
import fractions
import time
import win32gui
import ctypes
import datetime
import cv2
from global_vars import PSCX2, PES2, WIDTH, HEIGHT, X, Y

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
        self.output_ready = False

        self.recording = False
        self.ffmpeg_process = None
        self.output_file = None

        self.current_frame = None
        self.previous_frame = None
        self.time_base = None
        self.start_time = None
        self.last_pts = None
        self.frame_index = None

    def capture_frames(self):
        global X, Y, WIDTH, HEIGHT

        # rect = get_dpi_aware_window_rect("Calculator")
        # rect = get_dpi_aware_window_rect("Steam")

        # rect = get_dpi_aware_window_rect("20068 - VLC media player")
        # rect = get_dpi_aware_window_rect("WE6FE Classicos 2.0 (Hack Ed)")



        rect = get_dpi_aware_window_rect(PES2)
        # rect = get_dpi_aware_window_rect(PSCX2)
        if rect:
            print(f"Calculating rect....")
            X, Y, right, bottom = rect

            # # Region of the scoreboard of PES2
            # X += 220
            # Y += 220

            # Region of the player name (bottom center) of PES2
            X += 1090
            Y += 1814

            width =  right - X
            height = bottom - Y
            print(f"width {width} height {height}")
        else:
            print("rect is null")
     
        # Rescalling the input for specific frame location observation 
        # Values for PES2 scoreboard
        # WIDTH = width // 4 - 170
        # HEIGHT  = height // 4 - 420

        # Values for player name, center bottom of the screen
        WIDTH = width // 2 - 630
        HEIGHT  = height // 2 - 65
 
        # always making sure values are even!
        WIDTH = WIDTH - (WIDTH % 2)
        HEIGHT = HEIGHT - (HEIGHT % 2)

        video_size = f'{WIDTH}x{HEIGHT}'
        print(f'VIDEO SIZE: {video_size}')
        print(f'Y and X SIZE: {Y} , {X}')


        self.input_container = av.open('desktop',
                                        format='gdigrab',
                                        mode='r',
                                        options={
                                            'framerate': '30',
                                            'offset_x': str(X),
                                            'offset_y': str(Y),
                                            'video_size': video_size,  
                                            # 'video_size': '1920x1080',  
                                            # 'video_size': f'{width}x{height}',  
                                            'show_region': '0',
                                            # 'draw_mouse': '0',
                                        }
                                )


    # TODO: Rename this function to somethig like prepare output
    def setup_output(self):
        if not self.output_ready:
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

                self.output_ready = True
                print("Output stream is set up and ready")
                return True

            except Exception as e:
                print(f"Failed to prepare output stream: {e}")
                import traceback
                traceback.print_exc()
                return False


    # def stop_recording(self):
    #     if self.recording:
    #         # self.output_container.close()
    #         self.recording = False

    def start_recording(self):
        command = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'ddagrab=framerate=60',
                '-c:v', 'h264_nvenc',
                '-cq', '18',
                '-y',
                # '-t',
                # '10',
                'highlight_test.mp4'
            ]
        try:
            self.ffmpeg_process = subprocess.Popen(command,
                                                   stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE,
                                                   text=True,
                                                   bufsize=0
                                   )
            self.recording = True
            print('FFmpeg command executed successfully!')
            print('Recording screen.....')
            return True

            # print('Output:', self.ffmpeg_process.stdout)
        
        except Exception as e:
            print(f'Failed to start recording with FFmpeg: {e}')
        except FileNotFoundError:
            print('FFmpeg not found. Make sure it is installed.')
    

    def stop_recording(self):
        if self.ffmpeg_process is None:
            print('No FFmpeg process to stop')
            return False

        try:
            if self.recording:
                print('Sending "q" to stop recording...')
                self.ffmpeg_process.stdin.write('q\n')
                self.ffmpeg_process.stdin.flush()
                
                print(f"""
                STOPPED CURRENT FRAME: {np.sum(self.current_frame)}
                STOPPED PREVIOUS FRAME: {np.sum(self.previous_frame)}
                """)
                try:
                    # Wair for process to complete
                    # TODO: check if the timeout value is appropriate for our program logic
                    stdout, stderr = self.ffmpeg_process.communicate(timeout=2)

                    # print('Recording saved to ....')

                except subprocess.TimeoutExpired:
                    print(f"FFmpeg didn't respond to 'q', force terminating...")
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait()

                self.recording = False
                self.ffmpeg_process = None

                print('Recording stopped successfully')
                return True

        except Exception as e:
            print(f'Error stopping FFmpeg: {e}')
            
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process = None
            self.recording = False
            return False

    def manual_output_config(self):
        self.time_base = fractions.Fraction(1, 30)
        self.output_stream.time_base = self.time_base

        self.start_time = time.time()
        self.last_pts = -1

        self.frame_index = 0 

    # TO BE USED WHEN ANALYZING LOCAL REGION FRAMES FOR TESTING 
    def region_check(self, img_arr, frame):
        # ALSO TO BE USED FOR OBSERVING REGION FRAME VALUES CLOSELY 
        # if self.constant_changes(img_arr):
        if self.detect_changes_manual(img_arr, action='start'):
            print(f"""
            DETECTED CURRENT FRAME: {np.sum(self.current_frame)}
            DETECTED PREVIOUS FRAME: {np.sum(self.previous_frame)}
            """)

            if not self.recording:
                #using ffmpeg window command to test recording from here 
                self.start_recording()
            print("Recording")

        else:
            if self.recording:
                if self.detect_changes_manual(img_arr, action='stop'):
                    self.stop_recording()
                    # self.recording = False
                    # print('Stop recording')
                    # print("No changes, steady.")

        # else:
        #     if self.recording:
        #         self.stop_recording()
        #         print("Pattern matched. Stop recording")


        if self.recording:
            now = time.time()
            elapsed_time = now - self.start_time

            current_pts = int(elapsed_time / float(self.time_base))  
            # print(f"ELAPSED TIME: {elapsed_time} == CURRENT PTS: {current_pts}")

            if current_pts <= self.last_pts:
                return

            frame.pts = current_pts 
            frame.time_base = self.time_base

            packet = self.output_stream.encode(frame)


            self.output_container.mux(packet)

            self.last_pts = current_pts 


        self.previous_frame = img_arr
        # self.previous_frame = scoreboard



    def process_frames(self):
        # TODO: Maybe it does not make any sense to have this check here, we should only start recording? 
        if not self.output_ready:
            self.setup_output()
       
        self.manual_output_config()

        try:
            while True:
                try:
                    for frame in self.input_container.decode(video=0):
                        # current_time = time.time()


                        # TODO: Check why do we need to use numpy to convert frame to array 
                        img_arr = frame.to_ndarray(format='bgr24') 
                        # print(f'X and Y: {X} , {Y}')
                        # print(f'WIDTH and HEIGHT: {WIDTH} , {HEIGHT}')

                        # extract the scoreboard pixel region of the input stream so we can detect changes
                        # TODO: Check how these 3d arrays work and how they store the rgb pixel values
                        # scoreboard = img_arr[Y:Y+HEIGHT, X:X+WIDTH]
                        # print(f'SCOREBOARD: {scoreboard}')

                        # # Frame resizing logic with OpenCV cv2 lib. Keeping this here as doc only 
                        # new_width = .width + 1000
                        # new_height = frame.height + 1000 
                        #
                        # resized_arr = cv2.resize(img_arr, (new_width, new_height))
                        #
                        # new_frame = av.VideoFrame.from_ndarray(resized_arr, format='bgr24')
                        # frame = new_frame


                        # self.recording = False
                        # if self.detect_changes_cmd(scoreboard):

                        # if self.detect_changes_cmd(img_arr):
                        #
                        #     print(f"""
                        #     CURRENT FRAME: {np.sum(self.current_frame)}
                        #     PREVIOUS FRAME: {np.sum(self.previous_frame)}
                        #     """)
                        #     # if not self.recording:
                        #     for i in range(1500):
                        #         print("reckecking frame")
                        #         if not self.detect_changes_cmd(img_arr):
                        #             self.recording = False
                        #             break
                        #         self.recording = True
                        #
                        #     if self.recording:
                        #         print("Change detected. Start recording")
                        #         self.recording = True
                        #         self.start_recording()
                        #         time.sleep(2)
                        #     else:
                        #         print("false alert frame value")
                        #     # self.recording = True
                        #
                        # else:
                        #     if self.recording:
                        #         print(f"""
                        #         CURRENT FRAME: {np.sum(self.current_frame)}
                        #         PREVIOUS FRAME: {np.sum(self.previous_frame)}
                        #         """)
                        #         self.recording = False
                        #         self.stop_recording()
                        #         print('Stop recording')
                        #     # print("No changes, steady.")
                        #


                        self.region_check(img_arr, frame)


                except av.BlockingIOError:
                    pass
        except KeyboardInterrupt:
            print("Recording stopped by user")

        packet = self.output_stream.encode(None)
        self.output_container.mux(packet)

        self.input_container.close()
        self.output_container.close()

    def detect_changes_manual(self, current_frame, action=None):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = current_frame

        if action == 'start':
            if np.sum(current_frame) > 477000 and np.sum(current_frame) < 490000:
                return True
            else:
                return False

        if action == 'stop':
            # if np.sum(current_frame) < 430000:
            if np.sum(current_frame) < 6900:
                return True
            else:
                return False

        return False

        # return True

        # diff = np.sum(np.abs(current_frame - self.previous_frame))
        # return diff >  1 

    # TO BE USED TO CHECK REGION PIXEL COUNT DURING TESTING
    def constant_changes(self, current_frame):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = current_frame

        diff = np.sum(np.abs(current_frame - self.previous_frame))
        return diff >  1 
        





    def detect_changes_cmd(self, current_frame):
        # if self.previous_frame is None:
        #     print("previous_frame is None")
        #     return False

        # print("called")
        self.current_frame = current_frame
        print(f"""
CURRENT FRAME: {np.sum(current_frame)}
PREVIOUS FRAME: {np.sum(self.previous_frame)}
""")

        
        # if np.sum(current_frame) >= 6000000 and np.sum(current_frame) < 6001000:
        #     return False
        # elif np.sum(current_frame) > 6770000:
        #     return False
        if np.sum(self.current_frame) > 5830000 and np.sum(self.current_frame) < 5940000:
            return True
        #
        if np.sum(current_frame) < 800000:
            return False

        # return True

        return False

