import threading
import subprocess
import os
import random
# import time
from global_vars import OVERLAY_PATH, ERROR


def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return False


class SimpleOverlay:
    def __init__(self, x, y, video_path=None, width=None, height=None, duration=None):
        self.video_path = video_path
        self.x = x
        self.y = y
        self.target_width = width
        self.target_height = height
        self.duration = duration
        self.is_playing = False
        self.thread = None
        self.ffmpeg_process = None
        self.player_name = None

    def start(self):
        """Start playing the overlay"""
        if self.is_playing:
            return

        self.is_playing = True
        self.thread = threading.Thread(target=self._play_video)
        self.thread.daemon = True
        self.thread.start()


    def _play_video(self):
        # INPUT_PATH = 'overlay\\Desktop.mp4'        
        INPUT_PATH = ''        
        
        # NOTE Add check to confirm if overlay path and sub dirs exists and create path if they don't
        if self.player_name:
            self.player_name = self.player_name.lower()
            random.seed()
            index = random.randrange(1, 4)
            print(f'INDEX FOR FILES: {index}')
            print(f'Searching for {self.player_name + str(index)} ...')
            INPUT_PATH = find(f'{self.player_name + str(index)}.mp4', f'{OVERLAY_PATH}\\portugal')
            # print(f'INPUT PATH IN PLAY VIDEO: {INPUT_PATH}')
            if not INPUT_PATH:
                print(f'{ERROR}Player name: {self.player_name + str(index)} not found in path') 
                #TODO Check if this returns to the main menu
                return
            else:
                print(f'Found: {INPUT_PATH}')

        command = [
                'ffplay',
                '-noborder', 
                '-hide_banner',
                '-i', INPUT_PATH,
                '-left', str(self.x + 40),
                '-top', str(self.y + 150),
                # NOTE: We can use self.duration here if needed. 
                '-autoexit',
                '-ss', '0.5'
                # '-t',
                # '10',
        ]
        if INPUT_PATH:
            try:
                self.ffmpeg_process = subprocess.Popen(command)
                                      
                self.is_recording = True
                print('FFmpeg command executed successfully!')
                print('Rendering overlay screen.....')
                return True


            except Exception as e:
                print(f"❌ Error playing video: {e}")
            finally:
                self.is_playing = False
        else:
            self.is_playing = False
            print('INPUT PATH is empty or does not exist')




    def stop(self):
        """Stop playing the overlay"""
        if self.thread:
            self.thread.join()

        if self.ffmpeg_process is None:
            print('No FFmpeg process to stop')
            return False

        try:
            if self.is_playing:
                print('Sending "q" to stop playing the overlay...')

                self.ffmpeg_process.stdin.write('q\n')
                self.ffmpeg_process.stdin.flush()
                
                try:
                    # Wait for process to complete
                    stdout, stderr = self.ffmpeg_process.communicate(timeout=2)


                except subprocess.TimeoutExpired:
                    print(f"FFmpeg didn't respond to 'q', force terminating...")
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait()

                self.is_playing = False
                self.ffmpeg_process = None

                print('Overlay stopped successfully')
                return True
        except Exception as e:
            print('Error while force terminating FFmpeg process: {e}')
        finally:
            self.is_playing = False
            self.ffmpeg_process = None

