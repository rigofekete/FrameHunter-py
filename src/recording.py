import subprocess

import os
import sys
import threading
import queue

import av
import cv2

from collections import deque
import numpy as np
import fractions

import datetime
import time

from window_config import  get_dpi_aware_window_rect, crop_regions 

from global_vars import PCSX2, PES2, WE6, WE6FE
import global_vars


class ScreenRecorder:
    def __init__(self, buffer_seconds=10, fps=30):
        self.input_container = None
        self.output_container = None
        self.output_stream = None
        self.input_stream = None
        self.output_ready = False

        self.targets = []
        self.pts_arr = []

        self.is_recording = False
        self.ffmpeg_process = None
        
        # circlar buffer attributes
        self.buffer_seconds = buffer_seconds
        self.fps = fps
        self.max_buffer_frames = buffer_seconds * fps
        self.frame_buffer = deque(maxlen=self.max_buffer_frames)
        self.buffer_start_time = None

        self.buffer_lock = threading.Lock() 
        self.frame_queue = queue.Queue()

        # Buffer thread management
        self.buffer_thread = None
        self.stop_buffer_thread = threading.Event()
        self.save_buffer_trigger = threading.Event()
        self.is_buffer_thread_running = False

        self.current_frame = None
        self.previous_frame = None
        self.cropped_frame = None
        
        self.time_base = None
        self.start_time = None
        self.current_pts = None
        self.last_pts = None
        self.fps = fps

        self.detection_count = 10
        self.ok_detection = False

    def capture_frames(self):
        try:
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
            
            self.targets = crop_regions()
            print(f'targets 0 : {self.targets[0]}')

            video_size = f'{global_vars.WIDTH}x{global_vars.HEIGHT}'
            print(f'VIDEO SIZE: {video_size}')
            print(f'X and Y SIZE: {global_vars.X} , {global_vars.Y}')


            self.input_container = av.open('desktop',
                                            format='gdigrab',
                                            mode='r',
                                            options={
                                                'framerate': '30',
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

            # # NOTE: TEST BLOCK - To observ how many FPS are coming from the gdigrab input stream, use this:
            # count = 0
            # start = time.time()
            # for frame in self.input_container.decode(video=0):
            #     count += 1
            #     now = time.time()
            #     if now - start >= 5:
            #         break
            #
            # fps = count / (now - start)
            # print(f"Actual input FPS from gdigrab: {fps:.2f}")
        except Exception as e:
            print(f'Error setting up window config and input container and stream: {e}')
            sys.exit(1)
      
    def setup_output(self):
        if not self.output_ready:
            try:
                # now = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-')
                now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                # TODO: Add a check to confirm if folder already exists 
                output_path = os.path.abspath(f'output\\{now}.mp4')
                self.output_container = av.open(output_path, 'w')

                self.output_stream = self.output_container.add_stream('libx264', rate=30)
                self.output_stream.width = self.input_container.streams.video[0].width
                self.output_stream.height = self.input_container.streams.video[0].height
                self.output_stream.pix_fmt = 'yuv420p'
                # self.output_stream.codec_context.time_base = fractions.Fraction(1, 30)
                # self.output_stream.time_base = fractions.Fraction(1, 30)
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


    # FFmpeg cmd recording functions
    def start_recording(self):
        command = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'ddagrab=framerate=30',
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
            self.is_recording = True
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
            if self.is_recording:
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

                self.is_recording = False
                self.ffmpeg_process = None

                print('Recording stopped successfully')
                return True

        except Exception as e:
            print(f'Error stopping FFmpeg: {e}')
            
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process = None
            self.is_recording = False
            return False




    # Output pts and time base pre configuration 
    # TODO: Most likely we wont need this function at all, all of the attr can be set/reset in the const or if the
    # live recording stops with the failed detection
    def manual_output_config(self):
        if self.output_ready:
            self.time_base = fractions.Fraction(1, 30)
            self.output_stream.time_base = self.time_base
            # TODO check of this start time placed here is really only useful for the region check function for crops
            self.start_time = time.time()

            self.current_pts = -1
            self.last_pts = -1




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

        self.is_recording = True
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


    # Record to output from detected change, without circle buffer. 
    def record_frames_manual(self, img_arr, frame):
        now = time.time()
        elapsed_time = now - self.start_time

        self.current_pts = int(elapsed_time / float(self.time_base))
        # print(f'Elapsed_time: {elapsed_time} - Timebase {self.time_base} - Current pts: {current_pts}')

        if self.current_pts <= self.last_pts:
            return

        # if self.detect_changes_cmd(img_arr):
        if self.detect_changes_manual(img_arr):
            self.is_recording = True
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
            if self.is_recording:
                self.is_recording = False
                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)
                self.output_ready = False
                self.output_container.close()
                self.output_container = None
                self.output_stream = None
                return

        self.previous_frame = img_arr


    # TODO: Rename this function since we are not dealing with the circular buffer, only triggering the thread
    # and live recording to the main thread output file 
    def circle_buffer_frames(self, img_arr, frame):
        # NOTE: With the introduction of the circular buffer we wont be calculating new current pts here
        # any longer. The current pts is the last value received in the fill buffer function so we can have
        # continuity
        # now = time.time()
        # elapsed_time = now - self.start_time
        #
        # self.current_pts += int(elapsed_time / float(self.time_base))
        # print(f'Elapsed_time: {elapsed_time} - Timebase {self.time_base} - Current pts: {current_pts}')
        print(f"""
        CURRENT PTS: {self.current_pts}
        LAST PTS: {self.last_pts}
        """)

        # if self.current_pts <= self.last_pts and not self.ok_detection:
        #     return False



        # if self.detect_changes_cmd(img_arr):
        if self.detect_changes_manual(img_arr):
            if self.ok_detection:
                if not self.is_recording:
                    self.save_buffer_trigger.set()
                    self.start_time = time.time()
                    print('Detection triggered! Saving buffer in buffer thread....')

                self.ok_detection = True
                self.is_recording = True

                print(f"""
        CURRENT FRAME: {np.sum(img_arr)}
        PREVIOUS FRAME: {np.sum(self.previous_frame)}
        """)
                
                print('Saving live recording to the main thread ouput container')

                now = time.time()
                elapsed_time = now - self.start_time

                self.current_pts = int(elapsed_time / float(self.time_base))

                frame.pts = self.current_pts
                frame.time_base = self.time_base

                packet = self.output_stream.encode(frame)
                self.output_container.mux(packet)

                self.last_pts = self.current_pts

                # self.previous_frame = img_arr
                print(f"Encoded frame with PTS={frame.pts}")
                # return True
            else:
                self.detection_count -= 1
                if self.detection_count > 0:
                    print(f'double checking region frame count {self.detection_count}x')
                    # self.previous_frame = img_arr
                    self.start_time = 0
                    return False
                else:
                    self.ok_detection = True
            
        else:
            print("No frame changes detected, not recording")
            if self.is_recording:
                self.is_recording = False
                self.ok_detection = False

                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)
                self.output_ready = False
                self.output_container.close()
                self.output_container = None
                self.output_stream = None
        
        self.detection_count = 10
        self.previous_frame = img_arr
    


    
    #############################
    ## BUFFER THREAD FUNCTIONS ##
    #############################

    def start_buffer_thread(self):
        try:
            if not self.is_buffer_thread_running:
                self.stop_buffer_thread.clear()
                self.buffer_thread = threading.Thread(target=self._fill_buffer_thread, daemon=True)
                print('Buffer thread started')
                self.buffer_thread.start()
                self.is_buffer_thread_running = True
                self.buffer_start_time = time.time()
        except Exception as e:
            print(f'Error starting buffer thread: {e}')



    def _fill_buffer_thread(self):
        print('Fill buffer for continuous buffer management started in new thread')
        while not self.stop_buffer_thread.is_set():
            try:
                # Check for save trigger first, outside of frame processing
                if self.save_buffer_trigger.is_set():
                    try:
                        self._save_buffer_to_file()
                        self.save_buffer_trigger.clear()
                        self.self.pts_arr.clear()
                        self.buffer_start_time = time.time()
                    except Exception as e:
                        print(f'Error in save buffer: {e}')
                        # Don't let save buffer errors kill the thread
                        self.save_buffer_trigger.clear()  # Clear trigger anyway
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                        
                    with self.buffer_lock:
                        print('filling buffer....')
                         
                        frame_data = {
                                'frame': frame,
                                'timestamp': time.time(), 
                                'time_base': self.time_base
                        }

                        # TODO: Check if we can refill this array of ordered pts after each 
                        # save buffer trigger is set 
                        # NOTE: Place computed pts in a separate list/array so we can assign them in order 
                        # in the save buffer function (since we need to sort the frame buffer by timestamp)
                        if len(self.pts_arr) <= self.max_buffer_frames:
                            now = time.time()
                            elapsed_time = now - self.buffer_start_time
                            buffer_pts = int(elapsed_time / float(self.time_base))
                            self.pts_arr.append(buffer_pts)

                        self.frame_buffer.append(frame_data)

                except queue.Empty:
                    continue # no frame availabe, keep looping 
                except Exception as e:
                    print(f'Fill buffer thread error: {e}')

            except Exception as e:
                print(f'Save buffer trigger error: {e}')

        print('Buffer thread stopped')





    def _save_buffer_to_file(self):
        print('Save current buffer to pre-event file')
        with self.buffer_lock:
            if not self.frame_buffer:
                print('Buffer is empy, nothing to save')
                return

            print('Entering the save buffer area...')
            
            try:
                print('Entering the try scope of the save buffer file')
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                output_path = os.path.abspath(f'output\\pre-event-{timestamp}.mp4')

                buffer_output_container = av.open(output_path, 'w')

                buffer_output_stream = buffer_output_container.add_stream('libx264', rate=30)
                buffer_output_stream.width = self.input_container.streams.video[0].width
                buffer_output_stream.height = self.input_container.streams.video[0].height
                buffer_output_stream.pix_fmt = 'yuv420p'
                # NOTE: Adding this bit rate generates a low quality output that resembles an old vhs, 
                # should take advantage of this later :)
                # buffer_output_stream.codec_context.bit_rate = 2000000  # 2Mbps
                
                sorted_frames = sorted(self.frame_buffer, key=lambda x: x['timestamp'])

                print(f'Saving buffer with {len(sorted_frames)} frames')
                self.buffer_start_time = time.time()


                # NOTE: skip the last 25 buffer frames to record exactly up until the end of the play
                for i, frame_data in enumerate(sorted_frames[:-25]):
                    frame = frame_data['frame']
                    # TODO: Check if we can refill this array of ordered pts after each save buffer trigger is set 
                    frame.pts = self.pts_arr[i]
                    frame.time_base = frame_data['time_base']
                    
                    packet = buffer_output_stream.encode(frame)
                    buffer_output_container.mux(packet)

                    print(f'Encoded buffered frame with PTS={frame.pts}')


                self.frame_buffer.clear()

                for packet in buffer_output_stream.encode():
                    buffer_output_container.mux(packet)
                buffer_output_container.close()

                print(f'Successfully saved {len(sorted_frames)} frames from buffer')

            except Exception as e:
                print(f'Error saving buffer: {e}')






    def process_frames(self):
        # TODO: Maybe it does not make any sense to have this check here, we should only start recording? 
        # if not self.output_ready:
        self.setup_output()
        # TODO: Recheck if we really need this function at all
        self.manual_output_config()

        # Start buffer thread 
        self.start_buffer_thread()

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

                        try:
                            self.frame_queue.put_nowait(frame)
                        except queue.Full:
                            print('Buffer queue full, skipping frame')
                            pass

                        # LIST OF DIFFERENT FUNCTION CALLS FOR DIFFERENT PURPOSES
                        # self.record_frames_manual(img_arr, frame)
                        # self.record_frames_manual(nameplate_region, frame)
                        self.circle_buffer_frames(nameplate_region, frame)
                        # self.region_check(nameplate_region, frame, crop='yes')

                        if not self.is_recording and not self.output_ready:
                            self.setup_output()
                            # TODO: Recheck if we really need this function at all
                            self.manual_output_config()


                except av.BlockingIOError:
                    print('Blocking IO Error')
                    pass
                except Exception as e:
                    if self.is_recording and self.output_container:
                        print(f'Error processing frame: {e}')
                        print('Closing output container')
                        try:
                            self.is_recording = False
                            self.output_ready = False
                            self.input_container.close()
                            self.output_container.close()
                            sys.exit(1)
                            # pass
                        except:
                            self.input_container.close()
                            sys.exit(1)
                            # pass
                    else:
                        print(f'Error processing frame: {e}')
                        self.input_container.close()
                        sys.exit(1)
                        # pass
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
        # # NOTE: name these magic number values to something like nameplate_green_min/max
        # # pink nameplate
        # if ((np.sum(self.current_frame) > 2210000 and np.sum(self.current_frame) < 2228000) or
        # # blue nameplate night clear?
        #     (np.sum(self.current_frame) > 2627000 and np.sum(self.current_frame) < 2640000) or
        # # blue nameplate day clear 
        #     (np.sum(self.current_frame) > 2614000 and np.sum(self.current_frame) < 2630000) or
        # # green nameplate night clear 
        #     (np.sum(self.current_frame) > 1582000 and np.sum(self.current_frame) < 1604000) or 
        # # green nameplate day clear
        #     (np.sum(self.current_frame) > 1571000 and np.sum(self.current_frame) < 1583000) or
        # # yellow nameplate day clear
        #     (np.sum(self.current_frame) > 2065000 and np.sum(self.current_frame) < 2083000) 
        # ):
        #

        # NOTE: name these magic number values to something like nameplate_green_min/max
        # # pink nameplate day clear
        # if ((np.sum(self.current_frame) > 2524000 and np.sum(self.current_frame) < 2539000) or
        # pink nameplate night clear
        if ((np.sum(self.current_frame) > 2510000 and np.sum(self.current_frame) < 2535000) or
        # # blue nameplate night clear?
        #     (np.sum(self.current_frame) > 2627000 and np.sum(self.current_frame) < 2640000) or
        # blue nameplate day clear 
            (np.sum(self.current_frame) > 2985000 and np.sum(self.current_frame) < 2988000) or
        # green nameplate night clear 
            (np.sum(self.current_frame) > 1873000 and np.sum(self.current_frame) < 1897000) or 
        # # green nameplate day clear
        #     (np.sum(self.current_frame) > 1571000 and np.sum(self.current_frame) < 1583000) or
        # yellow nameplate night clear
            (np.sum(self.current_frame) > 2382000 and np.sum(self.current_frame) < 2405000) or 
        # yellow nameplate day clear
            (np.sum(self.current_frame) > 2400000 and np.sum(self.current_frame) < 2430000) 
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

