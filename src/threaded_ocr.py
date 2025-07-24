import threading
import queue
import time
import concurrent.futures
from dataclasses import dataclass


from global_vars import WARNING, SUCCESS, STOP, START, ERROR

@dataclass
class OCRResult:
    """Data class to store OCR detection results"""
    char_found: bool
    score_found: bool
    player_found: bool
    detected_text_char: str
    detected_text_score: str
    detected_text_player: str
    frame_counter: int
    timestamp: float

@dataclass  
class OCRTask:
    """Data class to store OCR task data"""
    nameplate_arr: any  # numpy array or image data
    min_arr: any        # numpy array or image data  
    player_arr: any     # numpy array or image data
    frame_counter: int
    timestamp: float

class ThreadedOCRProcessor:
    def __init__(self, txt_detector_class, txt_detector_args=None, txt_detector_kwargs=None, max_queue_size=10):
        self.txt_detector_class = txt_detector_class
        self.txt_detector_args = txt_detector_args or []
        self.txt_detector_kwargs = txt_detector_kwargs or {}
        
        # Task distribution queue - main queue where tasks come in
        self.ocr_queue = queue.Queue(maxsize=max_queue_size)
        
        # Separate internal queues for each detection type
        self.char_queue = queue.Queue(maxsize=max_queue_size)
        self.score_queue = queue.Queue(maxsize=max_queue_size)
        self.player_queue = queue.Queue(maxsize=max_queue_size)
        
        # Result storage for external consumption
        self.completed_results = []
        self.results_lock = threading.Lock()
        self.last_retrieved_index = -1  # Track what results have been retrieved
        
        # Shared result storage for each detection type
        self.char_result = None
        self.score_result = None 
        self.player_result = None
        self.result_lock = threading.Lock()
        
        # Control flags
        self.running = True
        
        # Start separate worker threads for each detection type
        self.char_thread = threading.Thread(target=self._char_worker, daemon=True)
        self.score_thread = threading.Thread(target=self._score_worker, daemon=True)
        self.player_thread = threading.Thread(target=self._player_worker, daemon=True)
        
        # Main coordinator thread
        self.coordinator_thread = threading.Thread(target=self._coordinator_worker, daemon=True)
        
        # Start all threads
        self.char_thread.start()
        self.score_thread.start()
        self.player_thread.start()
        self.coordinator_thread.start()
        
        print(f"OCR processor initialized with separate worker threads")
    
    def submit_ocr_task(self, nameplate_arr, min_arr, player_arr, frame_counter):
        """
        Submit OCR task for processing
        
        Args:
            nameplate_arr: Character nameplate image array
            min_arr: Score/minute image array  
            player_arr: Player name image array
            frame_counter: Frame counter for tracking
            
        Returns:
            bool: True if task was submitted successfully, False if queue is full
        """
        try:
            ocr_task = OCRTask(
                nameplate_arr=nameplate_arr,
                min_arr=min_arr,
                player_arr=player_arr,
                frame_counter=frame_counter,
                timestamp=time.time()
            )
            
            self.ocr_queue.put_nowait(ocr_task)
            return True
        except queue.Full:
            return False
        except Exception as e:
            print(f"Error submitting OCR task: {e}")
            return False
    
    def get_new_results(self):
        """
        Get any new OCR results that haven't been retrieved yet
        
        Returns:
            list: List of new OCRResult objects, empty list if no new results
        """
        with self.results_lock:
            if len(self.completed_results) > self.last_retrieved_index + 1:
                # Get all results after the last retrieved index
                new_results = self.completed_results[self.last_retrieved_index + 1:]
                self.last_retrieved_index = len(self.completed_results) - 1
                return new_results
            else:
                return []
    
    def _char_worker(self):
        """Dedicated worker thread for character detection"""
        try:
            detector = self.txt_detector_class(*self.txt_detector_args, **self.txt_detector_kwargs)
            print(f"CHAR detector initialized in thread {threading.get_ident()}")
        except Exception as e:
            print(f"Failed to initialize CHAR detector: {e}")
            return
            
        while self.running:
            try:
                task_data = self.char_queue.get(timeout=1.0)
                try:
                    result = detector.detect_char_in_region(task_data['array'])
                    with self.result_lock:
                        self.char_result = {
                            'found': result[0], 
                            'text': result[1], 
                            'timestamp': time.time(),
                            'frame_counter': task_data['frame_counter'],
                            'task_timestamp': task_data['timestamp']
                        }
                except Exception as e:
                    print(f"CHAR detection error: {e}")
                    with self.result_lock:
                        self.char_result = {
                            'found': False, 
                            'text': f"ERROR: {e}", 
                            'timestamp': time.time(),
                            'frame_counter': task_data['frame_counter'],
                            'task_timestamp': task_data['timestamp']
                        }
                self.char_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Char worker error: {e}")
                continue
        
        # Cleanup
        try:
            if hasattr(detector, 'cleanup_databases'):
                print('Cleaning up char database')
                detector.cleanup_databases()
        except Exception as e:
            print(f"Error cleaning up char detector: {e}")
    
    def _score_worker(self):
        """Dedicated worker thread for score detection"""
        try:
            detector = self.txt_detector_class(*self.txt_detector_args, **self.txt_detector_kwargs)
            print(f"SCORE detector initialized in thread {threading.get_ident()}")
        except Exception as e:
            print(f"Failed to initialize SCORE detector: {e}")
            return
            
        while self.running:
            try:
                task_data = self.score_queue.get(timeout=1.0)
                try:
                    result = detector.detect_score_in_region(task_data['array'])
                    with self.result_lock:
                        self.score_result = {
                            'found': result[0], 
                            'text': result[1], 
                            'timestamp': time.time(),
                            'frame_counter': task_data['frame_counter'],
                            'task_timestamp': task_data['timestamp']
                        }
                except Exception as e:
                    print(f"SCORE detection error: {e}")
                    with self.result_lock:
                        self.score_result = {
                            'found': False, 
                            'text': f"ERROR: {e}", 
                            'timestamp': time.time(),
                            'frame_counter': task_data['frame_counter'],
                            'task_timestamp': task_data['timestamp']
                        }
                self.score_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Score worker error: {e}")
                continue
        
        # Cleanup
        try:
            if hasattr(detector, 'cleanup_databases'):
                print("Cleaning up score database")
                detector.cleanup_databases()
        except Exception as e:
            print(f"Error cleaning up score detector: {e}")
    
    def _player_worker(self):
        """Dedicated worker thread for player detection"""
        try:
            detector = self.txt_detector_class(*self.txt_detector_args, **self.txt_detector_kwargs)
            print(f"PLAYER detector initialized in thread {threading.get_ident()}")
        except Exception as e:
            print(f"Failed to initialize PLAYER detector: {e}")
            return
            
        while self.running:
            try:
                task_data = self.player_queue.get(timeout=1.0)
                try:
                    result = detector.detect_player_in_region(task_data['array'])
                    with self.result_lock:
                        self.player_result = {
                            'found': result[0], 
                            'text': result[1], 
                            'timestamp': time.time(),
                            'frame_counter': task_data['frame_counter'],
                            'task_timestamp': task_data['timestamp']
                        }
                except Exception as e:
                    print(f"PLAYER detection error: {e}")
                    with self.result_lock:
                        self.player_result = {
                            'found': False, 
                            'text': f"ERROR: {e}", 
                            'timestamp': time.time(),
                            'frame_counter': task_data['frame_counter'],
                            'task_timestamp': task_data['timestamp']
                        }
                self.player_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Player worker error: {e}")
                continue
        
        # Cleanup
        try:
            if hasattr(detector, 'cleanup_databases'):
                print("Cleaning up player database")
                detector.cleanup_databases()
        except Exception as e:
            print(f"Error cleaning up player detector: {e}")
    
    def _coordinator_worker(self):
        """Main coordinator that distributes tasks and collects results"""
        while self.running:
            try:
                # Get OCR task from main queue
                task = self.ocr_queue.get(timeout=1.0)
                
                # Distribute to individual queues
                task_data_char = {
                    'array': task.nameplate_arr,
                    'frame_counter': task.frame_counter,
                    'timestamp': task.timestamp
                }
                task_data_score = {
                    'array': task.min_arr,
                    'frame_counter': task.frame_counter,
                    'timestamp': task.timestamp
                }
                task_data_player = {
                    'array': task.player_arr,
                    'frame_counter': task.frame_counter,
                    'timestamp': task.timestamp
                }
                
                # Submit tasks to individual worker queues
                try:
                    self.char_queue.put_nowait(task_data_char)
                except queue.Full:
                    print("Char queue full, skipping char detection")
                    
                try:
                    self.score_queue.put_nowait(task_data_score)
                except queue.Full:
                    print("Score queue full, skipping score detection")
                    
                try:
                    self.player_queue.put_nowait(task_data_player)
                except queue.Full:
                    print("Player queue full, skipping player detection")
                
                # Wait for all results to be ready (with timeout)
                start_time = time.time()
                timeout = 3.0
                
                while time.time() - start_time < timeout:
                    with self.result_lock:
                        if (self.char_result and 
                            self.score_result and 
                            self.player_result and
                            self.char_result['frame_counter'] == task.frame_counter and
                            self.score_result['frame_counter'] == task.frame_counter and
                            self.player_result['frame_counter'] == task.frame_counter):
                            
                            # All results ready for this frame
                            result = OCRResult(
                                char_found=self.char_result['found'],
                                score_found=self.score_result['found'],
                                player_found=self.player_result['found'],
                                detected_text_char=self.char_result['text'],
                                detected_text_score=self.score_result['text'],
                                detected_text_player=self.player_result['text'],
                                frame_counter=task.frame_counter,
                                timestamp=task.timestamp
                            )
                            
                            # Store completed result
                            with self.results_lock:
                                self.completed_results.append(result)
                                # Keep only recent results to prevent memory buildup
                                if len(self.completed_results) > 50:
                                    self.completed_results = self.completed_results[-25:]
                                    self.last_retrieved_index = max(-1, self.last_retrieved_index - 25)
                            break
                    
                    time.sleep(0.01)  # Small delay to avoid busy waiting
                else:
                    # Timeout - create result with whatever we have
                    with self.result_lock:
                        result = OCRResult(
                            char_found=self.char_result['found'] if self.char_result and self.char_result['frame_counter'] == task.frame_counter else False,
                            score_found=self.score_result['found'] if self.score_result and self.score_result['frame_counter'] == task.frame_counter else False,
                            player_found=self.player_result['found'] if self.player_result and self.player_result['frame_counter'] == task.frame_counter else False,
                            detected_text_char=self.char_result['text'] if self.char_result and self.char_result['frame_counter'] == task.frame_counter else "TIMEOUT",
                            detected_text_score=self.score_result['text'] if self.score_result and self.score_result['frame_counter'] == task.frame_counter else "TIMEOUT",
                            detected_text_player=self.player_result['text'] if self.player_result and self.player_result['frame_counter'] == task.frame_counter else "TIMEOUT",
                            frame_counter=task.frame_counter,
                            timestamp=task.timestamp
                        )
                        
                        with self.results_lock:
                            self.completed_results.append(result)
                            if len(self.completed_results) > 50:
                                self.completed_results = self.completed_results[-25:]
                                self.last_retrieved_index = max(-1, self.last_retrieved_index - 25)
                
                self.ocr_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f'{ERROR} Coordinator error: {e}')
                continue
    
    def stop(self):
        print(f'\n{WARNING} Stopping OCR processor...')
        self.running = False
        
        # Wait for threads to finish
        if self.char_thread.is_alive():
            self.char_thread.join(timeout=2.0)
        if self.score_thread.is_alive():
            self.score_thread.join(timeout=2.0)
        if self.player_thread.is_alive():
            self.player_thread.join(timeout=2.0)
        if self.coordinator_thread.is_alive():
            self.coordinator_thread.join(timeout=2.0)
        
        print(f'{STOP} OCR processor stopped')



# import threading
# import queue
# import time
# import concurrent.futures
# from dataclasses import dataclass
# from typing import List, Optional
# import numpy as np
#
# @dataclass
# class OCRTask:
#     nameplate_arr: np.ndarray
#     min_arr: np.ndarray
#     player_arr: np.ndarray
#     frame_counter: int
#     timestamp: float
#
# @dataclass 
# class OCRResult:
#     char_found: bool
#     score_found: bool
#     player_found: bool
#     detected_text_char: str
#     detected_text_score: str
#     detected_text_player: str
#     frame_counter: int
#     timestamp: float
#
# class ThreadedOCRProcessor:
#     def __init__(self, txt_detector_class, txt_detector_args=None, txt_detector_kwargs=None, max_queue_size=10):
#         # Store the class and initialization parameters instead of the instance
#         self.txt_detector_class = txt_detector_class
#         self.txt_detector_args = txt_detector_args or []
#         self.txt_detector_kwargs = txt_detector_kwargs or {}
#
#         self.ocr_queue = queue.Queue(maxsize=max_queue_size)
#         self.result_queue = queue.Queue(maxsize=max_queue_size)
#
#         # txt_detector will be created inside the worker thread
#         self.txt_detector = None
#
#         # TODO check what the daemon parameter is 
#         self.ocr_thread = threading.Thread(target=self._ocr_worker, daemon=True)
#         self.running = True
#         self.ocr_thread.start()
#
#         # Latest results (thread-safe with proper synchronization)
#         self._latest_result = None
#         self._result_lock = threading.Lock()
#
#     def _ocr_worker(self):
#         """Worker thread that processes OCR tasks"""
#         # Create txt_detector instance inside the worker thread
#         try:
#             self.txt_detector = self.txt_detector_class(*self.txt_detector_args, **self.txt_detector_kwargs)
#             print(f"OCR worker thread initialized txt_detector in thread {threading.get_ident()}")
#         except Exception as e:
#             print(f"Failed to initialize txt_detector in worker thread: {e}")
#             self.running = False
#             return
#
#         while self.running:
#             try:
#                 # Get OCR task with timeout to allow graceful shutdown
#                 task = self.ocr_queue.get(timeout=1.0)
#
#                 # Perform OCR detection using the thread-local txt_detector
#                 score_found, detected_text_score = self.txt_detector.detect_score_in_region(task.min_arr)
#                 player_found, detected_text_player = self.txt_detector.detect_player_in_region(task.player_arr)
#                 char_found, detected_text_char = self.txt_detector.detect_char_in_region(task.nameplate_arr)
#
#                 # Create result
#                 result = OCRResult(
#                     char_found=char_found,
#                     score_found=score_found,
#                     player_found=player_found,
#                     detected_text_char=detected_text_char,
#                     detected_text_score=detected_text_score,
#                     detected_text_player=detected_text_player,
#                     frame_counter=task.frame_counter,
#                     timestamp=task.timestamp
#                 )
#
#                 # Store latest result (thread-safe)
#                 with self._result_lock:
#                     self._latest_result = result
#
#                 # Also put in result queue for immediate consumption
#                 try:
#                     self.result_queue.put_nowait(result)
#                 except queue.Full:
#                     # If result queue is full, remove oldest and add new
#                     try:
#                         self.result_queue.get_nowait()
#                         self.result_queue.put_nowait(result)
#                     except queue.Empty:
#                         pass
#
#                 self.ocr_queue.task_done()
#
#             except queue.Empty:
#                 continue
#             except Exception as e:
#                 print(f"OCR worker error: {e}")
#                 continue
#
#         # Cleanup txt_detector when shutting down
#         try:
#             if hasattr(self.txt_detector, 'cleanup_databases'):
#                 self.txt_detector.cleanup_databases()
#         except Exception as e:
#             print(f"Error cleaning up txt_detector: {e}")
#
#
#     def submit_ocr_task(self, nameplate_arr, min_arr, player_arr, frame_counter):
#         """Submit OCR task to be processed asynchronously"""
#         if not self.running:
#             return False
#
#         task = OCRTask(
#             nameplate_arr=nameplate_arr.copy(),  # Copy arrays to avoid race conditions
#             min_arr=min_arr.copy(),
#             player_arr=player_arr.copy(),
#             frame_counter=frame_counter,
#             timestamp=time.time()
#         )
#
#         try:
#             # Try to add task, drop oldest if queue is full
#             self.ocr_queue.put_nowait(task)
#             return True
#         except queue.Full:
#             # Remove oldest task and add new one
#             try:
#                 self.ocr_queue.get_nowait()
#                 self.ocr_queue.put_nowait(task)
#                 return True
#             except queue.Empty:
#                 return False
#
#     def get_latest_result(self) -> Optional[OCRResult]:
#         """Get the most recent OCR result (thread-safe)"""
#         with self._result_lock:
#             return self._latest_result
#
#     def get_new_results(self) -> List[OCRResult]:
#         """Get all new results from the queue"""
#         results = []
#         while True:
#             try:
#                 result = self.result_queue.get_nowait()
#                 results.append(result)
#             except queue.Empty:
#                 break
#         return results
#
#     def shutdown(self):
#         """Gracefully shutdown the OCR thread"""
#         self.running = False
#         if self.ocr_thread.is_alive():
#             self.ocr_thread.join(timeout=2.0)
#
#
#
