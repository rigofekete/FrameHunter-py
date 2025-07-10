import subprocess
import os
import sys

import av
import cv2

import numpy as np
import fractions

import win32gui
import win32con
import ctypes

import datetime
import time

from global_vars import PCSX2, PES2, WIDTH, HEIGHT, X, Y

def get_dpi_aware_window_rect(title):
    try:
        hwnd = win32gui.FindWindow(None, title)
        if not hwnd:
            print("Window not found")

        # NOTE: Windows does not allow foreground call if window is shown and behind other windows
        # Because of this we need to force minimize and restore to be able to call it without errors...
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        # time.sleep(0.1)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f'Error in get_dpi_aware_window_rect(): {e}')
        sys.exit(1)
    
    # Get window rect values from the OS (in physical pixels)
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



def crop_regions(): 
    # TODO: IMPORTANT, handle errors for specific situations where the given coordinates
    # go beyond the available display margins
    # Crop the region of the player name (bottom center) of PES2
    x_nameplate = X - 10 
    y_nameplate = Y + 1795
    # x_nameplate = X + 40    
    # y_nameplate = Y + 1795
    width_nameplate = WIDTH // 2  - 1122
    height_nameplate = HEIGHT // 2 - 980  

    # always make sure values are even!
    width_nameplate = width_nameplate - (width_nameplate % 2)
    height_nameplate = height_nameplate - (height_nameplate % 2)

    return [
        {
            'name': 'nameplate',
            'x': x_nameplate, 
            'y': y_nameplate, 
            'width': width_nameplate, 
            'height': height_nameplate
        }
    ]

class ScreenRecorder:
    def __init__(self):
        self.input_container = None
        self.output_container = None
        self.output_stream = None
        self.input_stream = None
        self.output_ready = False

        self.targets = []

        self.recording = False
        self.ffmpeg_process = None

        self.current_frame = None
        self.previous_frame = None
        self.cropped_frame = None
        
        self.time_base = None
        self.start_time = None
        self.current_pts = None
        self.last_pts = None
        self.frame_index = None



    def capture_frames(self):
        global X, Y, WIDTH, HEIGHT

        # rect = get_dpi_aware_window_rect("Calculator")
        # rect = get_dpi_aware_window_rect("Steam")

        # rect = get_dpi_aware_window_rect("20068 - VLC media player")
        # rect = get_dpi_aware_window_rect("WE6FE Classicos 2.0 (Hack Ed)")


        # TODO: REFACTOR ALL THIS LOGIC INTO A FUNCTION TO GET RID OF THESE EXPOSED CODE LINES IN HERE 
        rect = get_dpi_aware_window_rect(PES2)
        # rect = get_dpi_aware_window_rect(PCSX2)
        if rect:
            print(f"Calculating rect....")
            X, Y, right, bottom = rect

            WIDTH =  right - X
            HEIGHT = bottom - Y
            print(f"width {WIDTH} height {HEIGHT}")
        else:
            print("rect is null")

        # TODO: Make a function or data structure to contain these different sets of values
        # Rescalling the input for specific frame location observation 
        # TODO: IMPORTANT, handle errors for specific situations where the given coordinates
        # go beyond the available display margins
        # Values for PES2 scoreboard
        # WIDTH = WIDTH // 4 - 170
        # HEIGHT  = HEIGHT // 4 - 420

        # # Values for player name, center bottom of the screen 
        # WIDTH = WIDTH // 2 
        # HEIGHT = HEIGHT // 2
        #
        # X += 1090
        # Y += 500
        #
        # # always making sure values are even!
        # WIDTH = WIDTH - (WIDTH % 2)
        # HEIGHT = HEIGHT - (HEIGHT % 2)

        self.targets = crop_regions()
        print(f'targets 0 : {self.targets[0]}')

        video_size = f'{WIDTH}x{HEIGHT}'
        print(f'VIDEO SIZE: {video_size}')
        print(f'X and Y SIZE: {X} , {Y}')


        self.input_container = av.open('desktop',
                                        format='gdigrab',
                                        mode='r',
                                        options={
                                            'framerate': '60',
                                            # 'probesize': '100M',      # Larger buffer
                                            # 'analyzeduration': '0',   # Skip analysis
                                            # 'fflags': 'nobuffer',     # Reduce buffering
                                            'offset_x': str(X),
                                            'offset_y': str(Y),
                                            'video_size': video_size,  
                                            # 'video_size': '1920x1080',  
                                            # 'video_size': f'{width}x{height}',  
                                            'show_region': '0',
                                            # 'draw_mouse': '0',
                                        }
                                )

        #NOTE: TEST BLOCK - To observ how many FPS are coming from the gdigrab input stream, use this:
        # count = 0
        # start = time.time()
        # for frame in self.input_container.decode(video=0):
        #     count += 1
        #     now = time.time()
        #     if now - start >= 5:
        #         break

        # fps = count / (now - start)
        # print(f"Actual input FPS from gdigrab: {fps:.2f}")
      
    def setup_output(self):
        if not self.output_ready:
            try:
                now = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-')
                output_path = os.path.abspath(f'output\\{now}.mp4')
                self.output_container = av.open(output_path, 'w')

                self.output_stream = self.output_container.add_stream('libx264', rate=60)
                self.output_stream.width = self.input_container.streams.video[0].width
                self.output_stream.height = self.input_container.streams.video[0].height
                # self.output_stream.width = self.input_container.streams.video[0].self.target[0]['width']
                # self.output_stream.height = self.input_container.streams.video[0].self.target[0]['height']
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
                                                   # bufsize=0
                                   )
            self.recording = True
            print('FFmpeg command executed successfully!')
            print('Recording screen.....')
            return True

        
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

    # NOTE: Maybe the code of this function should be placed at the start of the functions that use it
    # mainly because of the start_time value
    def manual_output_config(self):
        self.time_base = fractions.Fraction(1, 60)
        self.output_stream.time_base = self.time_base

        self.start_time = time.time()

        self.current_pts = -1
        self.last_pts = -1

        self.frame_index = 0 

    #
    # # TO BE USED WHEN ANALYZING LOCAL REGION FRAMES FOR TESTING 
    # def region_check(self, img_arr, frame):
    #
    #     # ALSO TO BE USED FOR OBSERVING REGION FRAME VALUES CLOSELY 
    #     # if self.constant_changes(img_arr):
    #
    #
    #     if self.detect_changes_manual(img_arr, action='start'):
    #         print(f"""
    #         DETECTED CURRENT FRAME: {np.sum(self.current_frame)}
    #         DETECTED PREVIOUS FRAME: {np.sum(self.previous_frame)}
    #         """)
    #
    #         if not self.recording:
    #             #NOTE: USING FFMPEG WINDOW COMMAND TO TEST RECORDING FROM HERE. 
    #             # WE NEED TO DECIDED WHERE TO PUT THIS START FFMPEG CMD RECORD TRIGGER
    #             self.start_recording()
    #         print("Recording")
    #
    #     else:
    #         if self.recording:
    #             self.stop_recording()
    #
    #
    #     if self.recording:
    #         now = time.time()
    #         elapsed_time = now - self.start_time
    #
    #         self.current_pts = int(elapsed_time / float(self.time_base))  
    #         # print(f"ELAPSED TIME: {elapsed_time} == CURRENT PTS: {current_pts}")
    #
    #         if self.current_pts <= self.last_pts:
    #             return
    #
    #         frame.pts = self.current_pts 
    #         frame.time_base = self.time_base
    #
    #         packet = self.output_stream.encode(frame)
    #         self.output_container.mux(packet)
    #
    #         self.last_pts = self.current_pts 
    #
    #
    #     self.previous_frame = img_arr
    #     # self.previous_frame = scoreboard

    # TO BE USED WHEN ANALYZING LOCAL REGION FRAMES FOR TESTING 
    def region_check(self, img_arr, frame):
        
        # ALSO TO BE USED FOR OBSERVING REGION FRAME VALUES CLOSELY 
        # if self.constant_changes(img_arr):

        now = time.time()
        elapsed_time = now - self.start_time

        self.current_pts = int(elapsed_time / float(self.time_base))  
        # print(f"ELAPSED TIME: {elapsed_time} == CURRENT PTS: {current_pts}")

        if self.current_pts <= self.last_pts:
            return

        if self.detect_changes_manual(img_arr, action='start'):
            print(f"""
            DETECTED CURRENT FRAME: {np.sum(self.current_frame)}
            DETECTED PREVIOUS FRAME: {np.sum(self.previous_frame)}
            """)

            frame.pts = self.current_pts 
            frame.time_base = self.time_base

            packet = self.output_stream.encode(frame)
            self.output_container.mux(packet)

            self.last_pts = self.current_pts 
        else:
            print('No frame changes detected, not recording')


        self.previous_frame = img_arr
        # self.previous_frame = scoreboard




    def record_frames_manual(self, img_arr, frame):
        now = time.time()
        elapsed_time = now - self.start_time

        # Compute pts based on actual elapsed time
        self.current_pts = int(elapsed_time / float(self.time_base))
        # print(f'Elapsed_time: {elapsed_time} - Timebase {self.time_base} - Current pts: {current_pts}')

        # # TODO: Lets try to tidy this thing up, maybe we need a funtcion to deal with this 
        # # Convert numpy array with the frame values back to a frame format in case we want to see exactly what region we are checking in the output
        # self.cropped_frame = av.VideoFrame.from_ndarray(img_arr, format='bgr24')
        # print(f'Cropped frame: {self.cropped_frame}')

        # Skip duplicate PTS
        if self.current_pts <= self.last_pts:
            return

        # if self.detect_changes_cmd(img_arr):
        if self.detect_changes_manual(img_arr):
        # if self.constant_changes(img_arr):
        # if True:
            print(f"""
    CURRENT FRAME: {np.sum(img_arr)}
    PREVIOUS FRAME: {np.sum(self.previous_frame)}
    """)
            frame.pts = self.current_pts
            frame.time_base = self.time_base
            
            # TODO: wrap these testing blocks in a function 
            # TEMPORARY ASSIGNMENT TO SEE THE CROPPED REGION IN OUTPUT
            ##########################################################
            # self.cropped_frame.pts = self.current_pts
            # self.cropped_frame.time_base = self.time_base
            # packet = self.output_stream.encode(self.cropped_frame)
            ##########################################################

            packet = self.output_stream.encode(frame)
            self.output_container.mux(packet)

            self.last_pts = self.current_pts
            print(f"Encoded frame with PTS={frame.pts}")
        else:
            print("No frame changes detected, not recording")

        self.previous_frame = img_arr
    




    def process_frames(self):
        # TODO: Maybe it does not make any sense to have this check here, we should only start recording? 
        if not self.output_ready:
            self.setup_output()
       
        self.manual_output_config()

        try:
            while True:
                try:
                    for frame in self.input_container.decode(video=0):


                        # TODO: Check why do we need to use numpy to convert frame to array 
                        img_arr = frame.to_ndarray(format='bgr24') 

                        # x = self.targets[0]['x'] - 500 
                        # y = self.targets[0]['y'] 
                        # width = self.targets[0]['width'] + 400
                        # height = self.targets[0]['height'] + 400

                        x = self.targets[0]['x'] 
                        y = self.targets[0]['y'] 
                        width = self.targets[0]['width']
                        height = self.targets[0]['height']
                        nameplate_region = img_arr[y:y+height, x:x+width]

                        # list of different function calls for different purposes
                        # self.record_frames_manual(img_arr, frame)
                        self.record_frames_manual(nameplate_region, frame)
                        # self.region_check(img_arr, frame)

                except av.BlockingIOError:
                    pass
        except KeyboardInterrupt:
            print("Recording stopped by user")

        packet = self.output_stream.encode(None)
        self.output_container.mux(packet)

        self.input_container.close()
        self.output_container.close()





    def detect_changes_manual(self, img_arr):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = img_arr
        print(f"""
CURRENT FRAME: {np.sum(self.current_frame)}
PREVIOUS FRAME: {np.sum(self.previous_frame)}
""")
        
        # pink nameplate
        if ((np.sum(self.current_frame) > 2210000 and np.sum(self.current_frame) < 2228000) or
        # blue nameplate
            (np.sum(self.current_frame) > 2627000 and np.sum(self.current_frame) < 2629000) or
        # green nameplate
            (np.sum(self.current_frame) > 1583000 and np.sum(self.current_frame) < 1585000)
        ):
            return True
        else:
            return False

        if np.sum(self.current_frame) < 6900:
            return True
        else:
            return False

        return False






    # TO BE USED TO CHECK REGION PIXEL COUNT DURING TESTING
    def constant_changes(self, current_frame):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = current_frame

        diff = np.sum(np.abs(current_frame - self.previous_frame))
        return diff >  1 
        





    # TODO: Think of this is of any use after we refactored the start/stop recording logic
    def detect_changes_cmd(self, current_frame):
        # if self.previous_frame is None:
        #     print("previous_frame is None")
        #     return False

        # print("called")
        self.current_frame = current_frame
        print(f"""
CURRENT FRAME: {np.sum(self.current_frame)}
PREVIOUS FRAME: {np.sum(self.previous_frame)}
""")
        
        if np.sum(self.current_frame) > 5830000 and np.sum(self.current_frame) < 5940000:
            return True
        #
        if np.sum(current_frame) < 800000:
            return False

        return False

