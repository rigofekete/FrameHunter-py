
import threading
import queue
import time
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class OCRTask:
    nameplate_arr: np.ndarray
    min_arr: np.ndarray
    player_arr: np.ndarray
    frame_counter: int
    timestamp: float

@dataclass 
class OCRResult:
    char_found: bool
    score_found: bool
    player_found: bool
    detected_text_char: str
    detected_text_score: str
    detected_text_player: str
    frame_counter: int
    timestamp: float

class ThreadedOCRProcessor:
    def __init__(self, txt_detector_class, txt_detector_args=None, txt_detector_kwargs=None, max_queue_size=10):
        # Store the class and initialization parameters instead of the instance
        self.txt_detector_class = txt_detector_class
        self.txt_detector_args = txt_detector_args or []
        self.txt_detector_kwargs = txt_detector_kwargs or {}
        
        self.ocr_queue = queue.Queue(maxsize=max_queue_size)
        self.result_queue = queue.Queue(maxsize=max_queue_size)
        
        # txt_detector will be created inside the worker thread
        self.txt_detector = None
        
        # TODO check what the daemon parameter is 
        self.ocr_thread = threading.Thread(target=self._ocr_worker, daemon=True)
        self.running = True
        self.ocr_thread.start()
        
        # Latest results (thread-safe with proper synchronization)
        self._latest_result = None
        self._result_lock = threading.Lock()
    
    def _ocr_worker(self):
        """Worker thread that processes OCR tasks"""
        # Create txt_detector instance inside the worker thread
        try:
            self.txt_detector = self.txt_detector_class(*self.txt_detector_args, **self.txt_detector_kwargs)
            print(f"OCR worker thread initialized txt_detector in thread {threading.get_ident()}")
        except Exception as e:
            print(f"Failed to initialize txt_detector in worker thread: {e}")
            self.running = False
            return
            
        while self.running:
            try:
                # Get OCR task with timeout to allow graceful shutdown
                task = self.ocr_queue.get(timeout=1.0)
                
                # Perform OCR detection using the thread-local txt_detector
                char_found, detected_text_char = self.txt_detector.detect_char_in_region(task.nameplate_arr)
                score_found, detected_text_score = self.txt_detector.detect_score_in_region(task.min_arr)
                player_found, detected_text_player = self.txt_detector.detect_player_in_region(task.player_arr)
                
                # Create result
                result = OCRResult(
                    char_found=char_found,
                    score_found=score_found,
                    player_found=player_found,
                    detected_text_char=detected_text_char,
                    detected_text_score=detected_text_score,
                    detected_text_player=detected_text_player,
                    frame_counter=task.frame_counter,
                    timestamp=task.timestamp
                )
                
                # Store latest result (thread-safe)
                with self._result_lock:
                    self._latest_result = result
                
                # Also put in result queue for immediate consumption
                try:
                    self.result_queue.put_nowait(result)
                except queue.Full:
                    # If result queue is full, remove oldest and add new
                    try:
                        self.result_queue.get_nowait()
                        self.result_queue.put_nowait(result)
                    except queue.Empty:
                        pass
                
                self.ocr_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"OCR worker error: {e}")
                continue
        
        # Cleanup txt_detector when shutting down
        try:
            if hasattr(self.txt_detector, 'cleanup_databases'):
                self.txt_detector.cleanup_databases()
        except Exception as e:
            print(f"Error cleaning up txt_detector: {e}")
    
    def submit_ocr_task(self, nameplate_arr, min_arr, player_arr, frame_counter):
        """Submit OCR task to be processed asynchronously"""
        if not self.running:
            return False
            
        task = OCRTask(
            nameplate_arr=nameplate_arr.copy(),  # Copy arrays to avoid race conditions
            min_arr=min_arr.copy(),
            player_arr=player_arr.copy(),
            frame_counter=frame_counter,
            timestamp=time.time()
        )
        
        try:
            # Try to add task, drop oldest if queue is full
            self.ocr_queue.put_nowait(task)
            return True
        except queue.Full:
            # Remove oldest task and add new one
            try:
                self.ocr_queue.get_nowait()
                self.ocr_queue.put_nowait(task)
                return True
            except queue.Empty:
                return False
    
    def get_latest_result(self) -> Optional[OCRResult]:
        """Get the most recent OCR result (thread-safe)"""
        with self._result_lock:
            return self._latest_result
    
    def get_new_results(self) -> List[OCRResult]:
        """Get all new results from the queue"""
        results = []
        while True:
            try:
                result = self.result_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        return results
    
    def shutdown(self):
        """Gracefully shutdown the OCR thread"""
        self.running = False
        if self.ocr_thread.is_alive():
            self.ocr_thread.join(timeout=2.0)



