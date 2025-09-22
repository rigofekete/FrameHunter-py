import subprocess

import os
import sys
import threading
import queue
import keyboard
import datetime
import time

import av

from collections import deque
import numpy as np
import fractions


from window_config import  get_dpi_aware_window_rect, crop_regions 
from text_detection import TextDetector
from simple_overlay import SimpleOverlay
from threaded_ocr import ThreadedOCRProcessor

from global_vars import (
        PCSX2, PES2, WE6, DAZN1_VLC, 
        OUTPUT_FOLDER, OVERLAY_PATH, LIVE_FOLDER, 
        MAX_REC_LIMIT, BLACK_FRAME, 
        LIVE, FULL,
        ERROR, STOP, WARNING, SUCCESS,
)

import global_vars 


class ScreenRecorder:
    def __init__(self, window=PES2, mode=FULL, crop='no', buffer_seconds=8, fps=30):
        # OCR Threading 
        self.ocr_processor = ThreadedOCRProcessor(
             # Replace with your actual class
            txt_detector_class=TextDetector,  
            # Add any positional arguments your TextDetector needs
            txt_detector_args=[],  
            # Add any keyword arguments your TextDetector needs
            txt_detector_kwargs={}  
        )
        # OCR state variables
        self.char_found = False
        self.score_found = False
        self.player_found = False
        self.ocr_frame_counter = 0

        
        # Streams
        self.input_container = None
        self.output_container = None
        self.output_stream = None
        # self.input_stream = None
        self.output_ready = False
        self.output_index = 1

        # Recoding attr
        self.mode = mode
        self.crop = crop
        self.is_recording = False
        self.recording_time = 0
        self.stop_recording = False
        self.ffmpeg_process = None
        self.fps = fps

        # Overlay
        self.is_overlay = False

        # Window name
        self.window = window

        # circlar buffer attributes
        self.buffer_seconds = buffer_seconds
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
        
        # Frames
        self.current_frame = None
        self.previous_frame = None
        self.cropped_frame = None
        
        self.time_base = None
        self.start_time = None
        self.current_pts = None
        self.last_pts = None

        self.detection_count = 10
        self.ok_detection = False
        # self.score_found = False
        # self.player_found = False
        # self.char_found = False

        # lists for target cropped dimensions and pts values
        self.targets = []
        self.pts_arr = []
        self.img_list = []


        # TODO Make a function to clean up the screenrecorder object




    def capture_frames(self):
        try:
            rect = get_dpi_aware_window_rect(self.window)
            if rect:
                print(f"Calculating rect....")
                global_vars.X, global_vars.Y, right, bottom = rect

                global_vars.WIDTH =  right - global_vars.X
                global_vars.HEIGHT = bottom - global_vars.Y
                print(f"width {global_vars.WIDTH} height {global_vars.HEIGHT}")
            else:
                print("rect is null")
                self.ocr_processor.stop()
                return False

            self.targets = crop_regions(self.window)
            # print(f'targets 0 : {self.targets[0]}')
            #
            video_size = f'{global_vars.WIDTH}x{global_vars.HEIGHT}'
            # print(f'VIDEO SIZE: {video_size}')
            print(f'X and Y SIZE: {global_vars.X} , {global_vars.Y}')

            self.input_container = av.open('desktop',
                                            format='gdigrab',
                                            mode='r',
                                            options={
                                                'framerate': str(self.fps),
                                                'offset_x': str(global_vars.X),
                                                'offset_y': str(global_vars.Y),
                                                'video_size': video_size,  
                                                'show_region': '0',
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
            # return False
            # sys.exit(1)
        return True
     
    def setup_output(self):
        if not self.output_ready:
            try:
                # now = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-')
                # now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                now = datetime.datetime.now().strftime("%H%M%S")
                # TODO: Add a check to confirm if folder already exists 
                if not os.path.exists(OUTPUT_FOLDER):
                    os.mkdir(OUTPUT_FOLDER)

                output_path = ""

                if self.mode == LIVE:
                    if not os.path.exists(LIVE_FOLDER):
                        os.mkdir(LIVE_FOLDER)
                    output_path = os.path.abspath(f'{LIVE_FOLDER}\\live-{now}.mp4')
                else:
                    output_path = os.path.abspath(f'{OUTPUT_FOLDER}\\{self.output_index}-live-{now}.mp4')

                self.output_container = av.open(output_path, 'w')

                self.output_stream = self.output_container.add_stream('libx264', rate=self.fps)
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
                # TODO Check this 
                import traceback
                traceback.print_exc()
                return False


    # FFmpeg cmd recording functions
    def start_recording(self):
        command = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'ddagrab=framerate={self.fps}',
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
            self.time_base = fractions.Fraction(1, self.fps)
            self.output_stream.time_base = self.time_base
            # TODO check if this start time placed here is really only useful for the region check function for crops
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
            print(f'Cropped frame: {self.cropped_frame}')

        if self.current_pts <= self.last_pts:
            return

        self.is_recording = True
#         print(f"""
# CURRENT FRAME: {np.sum(img_to_inspect)}
# PREVIOUS FRAME: {np.sum(self.previous_frame)}
# """)
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




    def rec_frames_ocr_threaded(self, img_list, frame):
        # NOTE Update value if list is resized in the future
        if len(img_list) < 3:
            raise Exception(f'img_list should have 3 elements/frame crops. Current size: {len(img_list)}')

        nameplate_arr, min_arr, player_arr = img_list

        print(f'NAMEPLATE_ARR: {nameplate_arr}')

        # Process any new OCR results (non-blocking)
        new_results = self.ocr_processor.get_new_results()
        # print(f'NEW RESULTS: {new_results}')
        if new_results:
            # Use the most recent result
            latest_result = new_results[-1]
            self.char_found = latest_result.char_found
            self.score_found = latest_result.score_found
            self.player_found = latest_result.player_found
            self.overlay.player_name = latest_result.detected_text_player
            # print(f'SCORE FOUND: {self.score_found} TEXT: {latest_result.detected_text_score}')
            # print(f'PLAYER FOUND: {self.player_found} TEXT: {latest_result.detected_text_player}')
            # print(f'CHAR FOUND: {self.char_found} TEXT: {latest_result.detected_text_char}')
            
        if not self.is_recording:
            # Submit OCR task every 8 frames (non-blocking)
            # if self.ocr_frame_counter % 1 == 0:
            if not self.overlay.is_playing:
                success = self.ocr_processor.submit_ocr_task(
                    nameplate_arr, min_arr, player_arr, self.ocr_frame_counter
                )
                if not success:
                    print("OCR queue full, skipping OCR for this frame")

            # Check for recording trigger
            if self.score_found and self.player_found:
                print(f'Starting recording - Score: {self.score_found}, Player: {self.player_found}')
                self.save_buffer_trigger.set()
                self.start_time = time.time()
                self.overlay.start()
                self.is_recording = True
                self.ocr_processor.delay_score_bool = False


            self.ocr_frame_counter = 0

        self.ocr_frame_counter += 1
        # Handle recording logic (same as before)
        if self.char_found and not self.is_recording and not self.overlay.is_playing:
            self.save_buffer_trigger.set()
            self.start_time = time.time()
            self.char_found = False  # Reset to avoid repeated triggers
            print('Detection triggered! Saving buffer in buffer thread....')
            self.is_recording = True
            self.recording_count = time.time()
            
        elif (self.is_recording and not self.stop_recording and
              (not self.detect_changes_trigger_end(nameplate_arr))):
            print('Saving live recording to the main thread output container')
            now = time.time()
            elapsed_time = now - self.start_time
            self.current_pts = int(elapsed_time / float(self.time_base))
            frame.pts = self.current_pts
            frame.time_base = self.time_base
            packet = self.output_stream.encode(frame)
            self.output_container.mux(packet)
            self.last_pts = self.current_pts

            #NOTE: Safe check to avoid having long continuous recording caused by unwanted behaviour
            print(f'REC TIME: {self.recording_time}')
            if self.recording_time > MAX_REC_LIMIT:
                self.stop_recording = True
                print(f'{ERROR} Live recording time limit reached: {MAX_REC_LIMIT}. Terminating recording for now')
                # print(f"Encoded frame with PTS={frame.pts}")
            
        else:
            # print("No frame changes detected, not recording")
            if self.is_recording:
                self.is_recording = False
                self.stop_recording = False
                self.recording_count = 0
                # ... your existing cleanup logic ...
                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)
                self.output_ready = False
                self.output_container.close()
                self.output_container = None
                self.output_stream = None
                self.overlay.stop()
                self.score_found = False
                self.player_found = False
                self.char_found = False

        self.previous_frame = nameplate_arr


    def rec_frames_px_count(self, img_arr, frame):
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
    



    
    ######################################
    ## CIRCULAR BUFFER THREAD FUNCTIONS ##
    ######################################

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
                        # NOTE: check if this array should be cleared or not 
                        self.pts_arr.clear()
                        self.buffer_start_time = time.time()
                    except Exception as e:
                        print(f'Error in save buffer: {e}')
                        # Don't let save buffer errors kill the thread
                        self.save_buffer_trigger.clear()  # Clear trigger anyway
                try:
                    frame = self.frame_queue.get(timeout=0.01)
                    with self.buffer_lock:
                        print('filling buffer....')
                         
                        frame_data = {
                                'frame': frame,
                                'timestamp': time.time(), 
                                'time_base': self.time_base
                        }

                        # TODO: Check if we can refill this array of ordered pts after each 
                        # save buffer trigger is set 
                        # NOTE: Computing pts in a separate list/array so we can assign them in order 
                        # in the save buffer function (since we need to sort the frame buffer by timestamp)
                        if len(self.pts_arr) <= self.max_buffer_frames:
                            now = time.time()
                            elapsed_time = now - self.buffer_start_time
                            buffer_pts = int(elapsed_time / float(self.time_base))
                            self.pts_arr.append(buffer_pts)

                        self.frame_buffer.append(frame_data)

                except queue.Empty:
                    # print('Empty queue, keep looping')
                    continue # no frame availabe, keep looping 
                except Exception as e:
                    print(f'Fill buffer thread error: {e}')

            except Exception as e: print(f'Save buffer trigger error: {e}')

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
                # timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                timestamp = time.strftime("%H%M%S")
                output_path = os.path.abspath(f'output\\{self.output_index}-pre-event-{timestamp}.mp4')
                self.output_index += 1

                buffer_output_container = av.open(output_path, 'w')

                buffer_output_stream = buffer_output_container.add_stream('libx264', rate=self.fps)
                buffer_output_stream.width = self.input_container.streams.video[0].width
                buffer_output_stream.height = self.input_container.streams.video[0].height
                buffer_output_stream.pix_fmt = 'yuv420p'
                # NOTE: Adding this bit rate generates a low quality output that resembles an old vhs, 
                # should take advantage of this later :)
                # buffer_output_stream.codec_context.bit_rate = 2000000  # 2Mbps
                
                sorted_frames = sorted(self.frame_buffer, key=lambda x: x['timestamp'])

                print(f'Saving buffer with {len(sorted_frames)} frames')
                print(f'Saving FRAME BUFFER with {len(self.frame_buffer)} frames')


                # self.buffer_start_time = time.time()
                # pts = 0

                # NOTE: skip the last 25 buffer frames to record exactly up until the end of the play
                for i, frame_data in enumerate(sorted_frames[:-25]):
                    frame = frame_data['frame']
                    # TODO: Check if we can refill this array of ordered pts after each save buffer trigger is set 
                    frame.pts = self.pts_arr[i]
                    # frame.pts = pts
                    frame.time_base = frame_data['time_base']
                    
                    packet = buffer_output_stream.encode(frame)
                    buffer_output_container.mux(packet)

                    # if i % 2 == 0:
                    #     pts += 1 
                    # else:
                    #     pts +=2
                    # pts += 2


                    print(f'Encoded buffered frame with PTS={frame.pts}')


                self.frame_buffer.clear()

                for packet in buffer_output_stream.encode():
                    buffer_output_container.mux(packet)
                buffer_output_container.close()

                print(f'Successfully saved {len(sorted_frames)} frames from buffer')

            except Exception as e:
                print(f'❌ Error saving buffer: {e}')






    def process_frames(self):
        # TODO: Maybe it does not make any sense to have this check here, we should only start recording? 
        # if not self.output_ready:
        self.setup_output()
        # TODO: Recheck if we really need this function at all
        self.manual_output_config()

        # Start buffer thread 
        self.start_buffer_thread()

        self.overlay = SimpleOverlay(
                # os.path.abspath(f'{OVERLAY_PATH}\\Desktop.mp4'),
                global_vars.X, global_vars.Y,
                global_vars.WIDTH, global_vars.HEIGHT, 
                duration=3
        )

        img_list = []

        try:
            while True:
                try:
                    for frame in self.input_container.decode(video=0):
                        # if keyboard.read_key() == 'q':
                        if keyboard.is_pressed('q'):
                            # TODO: Make a clean up function for this 
                            print('\nExiting highlights recording')
                            # sys.stdout.flush()
                            # try:
                            #     if self.output_stream and self.output_container:
                            #         for packet in self.output_stream.encode():
                            #             self.output_container.mux(packet)
                            #
                            # except Exception as e:
                            #     print(f'Error while cleaning up output stream: {e}')
                            #
                            # self.output_container.close()
                            # self.input_container.close()
                            # self.ocr_processor.stop()
                            self.close()
                            return 1


                        # TODO: Check why do we need to use numpy to convert frame to array 
                        img_arr = frame.to_ndarray(format='bgr24') 


                        print(f'TARGET 1 : {self.targets[0]}')

                        # Define the cropping frame region 
                        x = self.targets[0]['x'] 
                        y = self.targets[0]['y'] 
                        width = self.targets[0]['width']
                        height = self.targets[0]['height']
                        nameplate_region = img_arr[y:y+height, x:x+width]

                        x = self.targets[1]['x'] 
                        y = self.targets[1]['y'] 
                        width = self.targets[1]['width']
                        height = self.targets[1]['height']
                        min_region = img_arr[y:y+height, x:x+width]

                        x = self.targets[2]['x'] 
                        y = self.targets[2]['y'] 
                        width = self.targets[2]['width']
                        height = self.targets[2]['height']
                        name_region = img_arr[y:y+height, x:x+width]
                        # print(f'MIN REGION ARRAY: {min_region}')
                        img_list = [nameplate_region, min_region, name_region]

                        try:
                            self.frame_queue.put_nowait(frame)
                        except queue.Full:
                            print('Buffer queue full, skipping frame')
                            pass

                        if self.mode == FULL:
                            self.rec_frames_ocr_threaded(img_list, frame)
                            # self.rec_frames_ocr(nameplate_region, frame)
                            # self.rec_frames_ocr(img_list, frame)
                        elif self.mode == LIVE:
                            self.region_check(img_list[0], frame, crop=self.crop)
                            # self.region_check(img_list[2], frame, crop=self.crop)

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
                        # try:
                        #     self.is_recording = False
                        #     self.output_ready = False
                        #     self.input_container.close()
                        #     self.output_container.close()
                        #     # sys.exit(1)
                        #     # pass
                        # except:
                        #     self.input_container.close()
                        #     # sys.exit(1)
                        #     # pass
                        self.close()
                    else:
                        print(f'Error processing frame: {e}')
                        sys.exit(1)
                        self.input_container.close()
                        # sys.exit(1)
                        # pass
        except KeyboardInterrupt:
            print("Recording stopped by user")
        
        # try:
        #     if self.output_stream and self.output_container:
        #         for packet in self.output_stream.encode():
        #             self.output_container.mux(packet)
        # except Exception as e:
        #     print(f'Error while cleaning up output stream: {e}')
        #
        # self.input_container.close()
        # self.output_container.close()
        # self.ocr_processor.stop()
        self.close()




    def detect_changes_trigger_end(self, img_arr):
        if self.previous_frame is None:
            print("previous_frame is None")
            return False
        
        self.current_frame = img_arr
        print(f"""
        DETECT CHANGES TRIGGER END:
CURRENT FRAME: {np.sum(self.current_frame)}
PREVIOUS FRAME: {np.sum(self.previous_frame)}
""")

        # Scene transition black frame. Trigger point to stop live recording.
        if np.sum(self.current_frame) < BLACK_FRAME:
        # if np.sum(self.current_frame) < 690000:
            return True
        else:
            return False
    
    def close(self):
        print(f'{WARNING} Cleaning up the recorder object....')
        try:
            if self.output_stream and self.output_container:
                for packet in self.output_stream.encode():
                    self.output_container.mux(packet)
        except Exception as e:
            print(f'{ERROR} Error while cleaning up output stream: {e}')

        self.input_container.close()
        self.output_container.close()
        self.ocr_processor.stop()

        print(f'{STOP} All streams and containers closed!')

#
#
#
#     def detect_changes_manual(self, img_arr):
#         if self.previous_frame is None:
#             print("previous_frame is None")
#             return False
#
#         self.current_frame = img_arr
#         print(f"""
# CURRENT FRAME: {np.sum(self.current_frame)}
# PREVIOUS FRAME: {np.sum(self.previous_frame)}
# """)
#         # NOTE: name these magic number values to something like nameplate_green_min/max
#         # # pink nameplate day clear
#         # if ((np.sum(self.current_frame) > 2524000 and np.sum(self.current_frame) < 2539000) or
#         # pink nameplate night clear
#         if ((np.sum(self.current_frame) > 2510000 and np.sum(self.current_frame) < 2535000) or
#         # # blue nameplate night clear?
#         #     (np.sum(self.current_frame) > 2627000 and np.sum(self.current_frame) < 2640000) or
#         # blue nameplate day clear 
#             (np.sum(self.current_frame) > 2970000 and np.sum(self.current_frame) < 2988000) or
#         # green nameplate night clear 
#             (np.sum(self.current_frame) > 1873000 and np.sum(self.current_frame) < 1897000) or 
#         # # green nameplate day clear
#         #     (np.sum(self.current_frame) > 1571000 and np.sum(self.current_frame) < 1583000) or
#         # yellow nameplate night clear
#             (np.sum(self.current_frame) > 2382000 and np.sum(self.current_frame) < 2405000) or 
#         # yellow nameplate day clear
#             (np.sum(self.current_frame) > 2400000 and np.sum(self.current_frame) < 2430000) 
#         ):
#             return True
#         else:
#             return False
#
#         # Scene transition black frame. Trigger point to stop live recording.
#         if np.sum(self.current_frame) < 6900:
#             return True
#         else:
#             return False
#
#         # return False
#
#     # TODO: Think of this is of any use if we decide to use the ffmpeg process cmd commands  
#     def detect_changes_cmd(self, current_frame):
#         # if self.previous_frame is None:
#         #     print("previous_frame is None")
#         #     return False
#
#         # print("called")
#         self.current_frame = current_frame
#         print(f"""
# CURRENT FRAME: {np.sum(self.current_frame)}
# PREVIOUS FRAME: {np.sum(self.previous_frame)}
# """)
#
#         if np.sum(self.current_frame) > 5830000 and np.sum(self.current_frame) < 5940000:
#             return True
#         #
#         if np.sum(current_frame) < 800000:
#             return False
#
#         return False

