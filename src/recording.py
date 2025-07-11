import subprocess
import os
import sys

import av
import cv2

import numpy as np
import fractions

import datetime
import time

from window_config import  get_dpi_aware_window_rect, crop_regions 

from global_vars import PCSX2, PES2, WE6, WE6FE
import global_vars


class ScreenRecorder:
    def __init__(self):
        self.input_container = None
        self.output_container = None
        self.output_stream = None
        self.input_stream = None
        self.output_ready = False

        self.targets = []

        self.isRecording = False
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
        # rect = get_dpi_aware_window_rect("Calculator")
        # rect = get_dpi_aware_window_rect("Steam")

        # rect = get_dpi_aware_window_rect("20068 - VLC media player")
        # rect = get_dpi_aware_window_rect("WE6FE Classicos 2.0 (Hack Ed)")


        # TODO: REFACTOR ALL THIS LOGIC INTO A FUNCTION TO GET RID OF THESE EXPOSED CODE LINES IN HERE 
        rect = get_dpi_aware_window_rect(PES2)
        # rect = get_dpi_aware_window_rect(WE6)
        # rect = get_dpi_aware_window_rect(WE6FE)
        # rect = get_dpi_aware_window_rect(PCSX2)
        if rect:
            print(f"Calculating rect....")
            global_vars.X, global_vars.Y, right, bottom = rect

            global_vars.WIDTH =  right - global_vars.X
            global_vars.HEIGHT = bottom - global_vars.Y
            print(f"width {global_vars.WIDTH} height {global_vars.HEIGHT}")
        else:
            print("rect is null")
        
        print(f'X : {global_vars.X}')
        self.targets = crop_regions()
        print(f'targets 0 : {self.targets[0]}')

        video_size = f'{global_vars.WIDTH}x{global_vars.HEIGHT}'
        print(f'VIDEO SIZE: {video_size}')
        print(f'X and Y SIZE: {global_vars.X} , {global_vars.Y}')


        self.input_container = av.open('desktop',
                                        format='gdigrab',
                                        mode='r',
                                        options={
                                            'framerate': '60',
                                            # 'probesize': '100M',      # Larger buffer
                                            # 'analyzeduration': '0',   # Skip analysis
                                            # 'fflags': 'nobuffer',     # Reduce buffering
                                            'offset_x': str(global_vars.X),
                                            'offset_y': str(global_vars.Y),
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
            self.isRecording = True
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
            if self.isRecording:
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

                self.isRecording = False
                self.ffmpeg_process = None

                print('Recording stopped successfully')
                return True

        except Exception as e:
            print(f'Error stopping FFmpeg: {e}')
            
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process = None
            self.isRecording = False
            return False

    def manual_output_config(self):
        self.time_base = fractions.Fraction(1, 60)
        self.output_stream.time_base = self.time_base

        self.start_time = time.time()

        self.current_pts = -1
        self.last_pts = -1

        self.frame_index = 0 





    # TO BE USED WHEN ANALYZING LOCAL REGION FRAMES FOR TESTING 
    # If crop is set to 'no' the img_to_inspect wont be used and converted to a frame 
    # since we will output only the full original frame from the input 
    def region_check(self, img_to_inspect, frame, crop='yes'):
        now = time.time()
        elapsed_time = now - self.start_time

        self.current_pts = int(elapsed_time / float(self.time_base))
        # print(f'Elapsed_time: {elapsed_time} - Timebase {self.time_base} - Current pts: {current_pts}')

        # Convert numpy array with the frame values back to a frame format 
        # in case we want to see exactly what region we are checking in the output
        if crop == 'yes':
            self.cropped_frame = av.VideoFrame.from_ndarray(img_to_inspect, format='bgr24')
            # print(f'Cropped frame: {self.cropped_frame}')

        if self.current_pts <= self.last_pts:
            return

        self.isRecording = True
        print(f"""
CURRENT FRAME: {np.sum(img_to_inspect)}
PREVIOUS FRAME: {np.sum(self.previous_frame)}
""")
        frame.pts = self.current_pts
        frame.time_base = self.time_base
        
        packet = None
        if crop == 'yes':
            self.cropped_frame.pts = self.current_pts
            self.cropped_frame.time_base = self.time_base
            packet = self.output_stream.encode(self.cropped_frame)
        elif crop == 'no':
            packet = self.output_stream.encode(frame)

        self.output_container.mux(packet)

        self.last_pts = self.current_pts

        print(f"Encoded frame with PTS={frame.pts}")

        self.previous_frame = img_to_inspect





    def record_frames_manual(self, img_arr, frame):
        now = time.time()
        elapsed_time = now - self.start_time

        self.current_pts = int(elapsed_time / float(self.time_base))
        # print(f'Elapsed_time: {elapsed_time} - Timebase {self.time_base} - Current pts: {current_pts}')

        if self.current_pts <= self.last_pts:
            return

        # if self.detect_changes_cmd(img_arr):
        if self.detect_changes_manual(img_arr):
            self.isRecording = True
            print(f"""
    CURRENT FRAME: {np.sum(img_arr)}
    PREVIOUS FRAME: {np.sum(self.previous_frame)}
    """)
            frame.pts = self.current_pts
            frame.time_base = self.time_base
            
            packet = self.output_stream.encode(frame)
            self.output_container.mux(packet)

            self.last_pts = self.current_pts

            # self.previous_frame = img_arr
            print(f"Encoded frame with PTS={frame.pts}")
        else:
            print("No frame changes detected, not recording")
            if self.isRecording:
                self.isRecording = False
                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)
                self.output_ready = False
                self.output_container.close()
                self.output_container = None
                self.output_stream = None
                return

        self.previous_frame = img_arr
    



    def process_frames(self):
        # TODO: Maybe it does not make any sense to have this check here, we should only start recording? 
        # if not self.output_ready:
        self.setup_output()
        self.manual_output_config()

        try:
            while True:
                try:
                    for frame in self.input_container.decode(video=0):
                        # TODO: Check why do we need to use numpy to convert frame to array 
                        img_arr = frame.to_ndarray(format='bgr24') 

                        # Define the cropping frame region 
                        x = self.targets[0]['x'] 
                        y = self.targets[0]['y'] 
                        width = self.targets[0]['width']
                        height = self.targets[0]['height']
                        nameplate_region = img_arr[y:y+height, x:x+width]

                        # LIST OF DIFFERENT FUNCTION CALLS FOR DIFFERENT PURPOSES
                        # self.record_frames_manual(img_arr, frame)
                        self.record_frames_manual(nameplate_region, frame)
                        # self.region_check(nameplate_region, frame, crop='yes')

                        if not self.isRecording:
                            self.setup_output()
                            self.manual_output_config()

                except av.BlockingIOError:
                    print('Blocking IO Error')
                    pass
                except Exception as e:
                    if self.isRecording and self.output_container:
                        print(f'Error processing frame: {e}')
                        print('Closing output container')
                        try:
                            self.isRecording = False
                            self.output_ready = False
                            self.output_container.close()
                            pass
                        except:
                            pass
                    else:
                        print(f'Error processing frame: {e}')
                        pass
        except KeyboardInterrupt:
            print("Recording stopped by user")
        
        try:
            if self.output_stream and self.output_container:
                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)
                    self.output_container.close()
        except Exception as e:
            print(f'Error while cleaning up output stream: {e}')

        self.input_container.close()





    def detect_changes_manual(self, img_arr):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = img_arr
        print(f"""
CURRENT FRAME: {np.sum(self.current_frame)}
PREVIOUS FRAME: {np.sum(self.previous_frame)}
""")
        # NOTE: name these magic number values to something like nameplate_green_min/max
        # pink nameplate
        if ((np.sum(self.current_frame) > 2210000 and np.sum(self.current_frame) < 2228000) or
        # blue nameplate night clear?
            (np.sum(self.current_frame) > 2627000 and np.sum(self.current_frame) < 2640000) or
        # blue nameplate day clear 
            (np.sum(self.current_frame) > 2614000 and np.sum(self.current_frame) < 2619999) or
        # green nameplate night clear 
            (np.sum(self.current_frame) > 1583000 and np.sum(self.current_frame) < 1604000) or
        # green nameplate day clear
            (np.sum(self.current_frame) > 1571000 and np.sum(self.current_frame) < 1583000) or
        # yellow nameplate day clear
            (np.sum(self.current_frame) > 2075000 and np.sum(self.current_frame) < 2083000) 
        ):
            return True
        else:
            return False

        # Scene transition black frame
        if np.sum(self.current_frame) < 6900:
            return True
        else:
            return False

        return False


    #NOTE: We probably wont need this any longer 
    # TO BE USED TO CHECK REGION PIXEL COUNT DURING TESTING
    def constant_changes(self, current_frame):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = current_frame

        diff = np.sum(np.abs(current_frame - self.previous_frame))
        return diff >  1 
        

    # TODO: Think of this is of any use if we decide to use the ffmpeg process cmd commands  
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

