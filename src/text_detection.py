import os
import time
import sys

import cv2
import sqlite3
import pytesseract
from global_vars import DB_PATH


# TODO: DB files need to be reset when starting the program!

class TextDetector:
    def __init__(self):
        # Setup Tessaract
        try:
            # r at the start of the string stands for raw literal string. We do this to treat \ as literal chars
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        except Exception as e:
            print(f'Undefined path to tesseract.exe. Check if OCR is installed in you OS. Error: {e}')
            sys.exit(1)

        # OCR configuration with PSM 10 Mode, ideal for single character detection 
        self.ocr_config = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '

        # self.ocr_config_score = '--psm 10 -c tessedit_char_whitelist=0123456789O '
        self.ocr_config_score = '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789. '
        
        self.ocr_config_player = '--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz. '
        # self.ocr_config_player = '--psm 8 -c tessedit_char_whitelist=0123456789Ii '

        #NOTE:
        # PSM MODES ##
        ##############
        # PSM 8	Single textline (can detect multiple characters)
        # PSM 10 Single character (treats entire image as one character)
        # PSM 7 Treat the Image as a Single Text Line
        # PSM 11 Sparse Text: Find as Much Text as Possible in No Particular Order


        # Initialize player database
        self.setup_char_database()
        self.setup_score_database()
        self.setup_player_database()
        
        # Detection parameters
        self.min_confidence = 50
        self.last_detection_time = 0






    def setup_char_database(self):
        """Setup simple CHAR detection database"""
        
        if not os.path.exists(DB_PATH):
            os.mkdir(DB_PATH)

        self.conn_char = sqlite3.connect(f'{DB_PATH}\\char_detections.db')

        cursor = self.conn_char.cursor()
        
        # Create table for CHAR detections
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS char_detections (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                detected_text TEXT,
                confidence INTEGER,
                frame_saved INTEGER DEFAULT 0
            )
        ''')
        
        # Create table for target patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS target_patterns (
                id INTEGER PRIMARY KEY,
                pattern TEXT UNIQUE,
                active INTEGER DEFAULT 1
            )
        ''')
        
        # Add target patterns of single chars
        patterns = [
            ("DF", 1),
            ("MF", 1),
            ("FW", 1),
            ("GK", 1),
            # ("D", 1),
            # ("M", 1),
            # ("F", 1),
            # ("f", 1),
            # ("W", 1),
            # ("w", 1),
            # ("G", 1),
            # ("k", 1),
            # ("K", 1),

        ]
        
        cursor.executemany(
            'INSERT OR IGNORE INTO target_patterns (pattern, active) VALUES (?, ?)',
            patterns
        )
        
        self.conn_char.commit()




    def setup_score_database(self):
        """Setup simple SCORE detection database"""

        if not os.path.exists(DB_PATH):
            os.mkdir(DB_PATH)



        self.conn_score = sqlite3.connect(f'{DB_PATH}\\score_detections.db')

        cursor = self.conn_score.cursor()

        # Create table for SCORE detections
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS score_detections (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                detected_text TEXT,
                confidence INTEGER,
                frame_saved INTEGER DEFAULT 0
            )
        ''')

        # Create table for target patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS target_patterns (
                id INTEGER PRIMARY KEY,
                pattern TEXT UNIQUE,
                active INTEGER DEFAULT 1
            )
        ''')

        # Add target patterns of single chars
        patterns = [
            ("min.", 1),
            ("MIN.", 1),
            # ("O", 1),
            # ("1", 1),
            # ("2", 1),
            # ("3", 1),
            # ("4", 1),
            # ("5", 1),
            # ("6", 1),
            # ("7", 1),
            # ("8", 1),
            # ("9", 1),
        ]

        cursor.executemany(
            'INSERT OR IGNORE INTO target_patterns (pattern, active) VALUES (?, ?)',
            patterns
        )

        self.conn_score.commit()



    def setup_player_database(self):
        """Setup simple PLAYER detection database"""

        if not os.path.exists(DB_PATH):
            os.mkdir(DB_PATH)


        self.conn_player = sqlite3.connect(f'{DB_PATH}\\player_detections.db')

        cursor = self.conn_player.cursor()

        # Create table for SCORE detections
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS score_detections (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                detected_text TEXT,
                confidence INTEGER,
                frame_saved INTEGER DEFAULT 0
            )
        ''')

        # Create table for target patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS target_patterns (
                id INTEGER PRIMARY KEY,
                pattern TEXT UNIQUE,
                active INTEGER DEFAULT 1
            )
        ''')

        # Add target patterns of single chars
        patterns = [
            # ("S.", 1),
            ("CONCEICAO", 1),
            # ("conceicao", 1),
            ("PAULETA", 1),
            # ("Pauleta", 1),
            # ("pauleta", 1),
            # ("Joao", 1),
            ("JOAO", 1),
            # ("pinto", 1),
            # ("Pinto", 1),
            ("PINTO", 1),
            # ("S. CONCEICAO", 1),
            # ("S.CONCEICAO", 1),
            # ("S.Conceicao", 1),
            # ("S. Conceicao", 1),
            # ("Bierhoff", 1),
            # ("BIERHOFF", 1),
            # ("S. CONCEICAO", 1),
            # ("S. CONCEICAO", 1),
            # ("S.CONCEICAO", 1),
            # ("S.Conceicao", 1),
            # ("S. Conceicao", 1),
            # ("Gujovic", 1),
            # ("GUJOVIC", 1),
            # ("gujovic", 1),
            # ("GIULY", 1),
            # ("Giuly", 1),
            # ("8Giuly", 1),
            # ("8GIULY", 1),
            # ("8 GIULY", 1),
            # ("8 Giuly", 1),
            # ("O", 1),
            # ("1", 1),
            # ("2", 1),
            # ("3", 1),
            # ("4", 1),
            # ("5", 1),
            # ("6", 1),
            # ("7", 1),
            # ("8", 1),
            # ("9", 1),
        ]

        cursor.executemany(
            'INSERT OR IGNORE INTO target_patterns (pattern, active) VALUES (?, ?)',
            patterns
        )

        self.conn_player.commit()



    def detect_char_in_region(self, nameplate_region):
        """Detect letters in cropped region"""
        try:

            # Upscale the region first
            # Experiment with different values (2-4 typically work well)
            scale_factor = 4  
            height, width = nameplate_region.shape[:2]
            upscaled_region = cv2.resize(
                nameplate_region, 
                (width * scale_factor, height * scale_factor), 
                interpolation=cv2.INTER_CUBIC
            )

            # denoised_region = cv2.fastNlMeansDenoisingColored(upscaled_region, None, 10, 10, 7, 15)
            #
            # # Preprocess image for better OCR
            # gray = cv2.cvtColor(denoised_region, cv2.COLOR_BGR2GRAY)
            #
            # thresh = cv2.adaptiveThreshold(
            #     gray,                           # Input grayscale image
            #     255,                           # Maximum value assigned to pixel
            #     cv2.ADAPTIVE_THRESH_GAUSSIAN_C, # Adaptive method
            #     cv2.THRESH_BINARY,             # Threshold type
            #     11,                            # Block size (neighborhood area)
            #     2                              # C constant subtracted from mean
            # )

            # Preprocess image for better OCR
            # gray = cv2.cvtColor(nameplate_region, cv2.COLOR_BGR2GRAY)
            gray = cv2.cvtColor(upscaled_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            self.min_confidence = 40

            # Extract text using OCR
            results = pytesseract.image_to_data(
                thresh, 
                output_type=pytesseract.Output.DICT,
                config=self.ocr_config
            )
            
            # Check each detected text piece
            for i in range(len(results['text'])):
                confidence = int(results['conf'][i])
                text = results['text'][i].strip().upper()
                
                if confidence > self.min_confidence and text:
                    # Check against target patterns
                    if self.check_char_patterns(text):
                        # Log detection to database
                        self.log_char_detection(text, confidence)
                        return True, text
            
            return False, None
            
        except Exception as e:
            print(f"CHAR detection error: {e}")
            return False, None


    def detect_score_in_region(self, nameplate_region):
        """Detect score in cropped region"""
        try:
            # Upscale the region first
            scale_factor = 3  # Experiment with different values (2-4 typically work well)
            height, width = nameplate_region.shape[:2]
            upscaled_region = cv2.resize(
                nameplate_region, 
                (width * scale_factor, height * scale_factor), 
                interpolation=cv2.INTER_CUBIC
            )

            # Preprocess image for better OCR
            gray = cv2.cvtColor(upscaled_region, cv2.COLOR_BGR2GRAY)
            # gray = cv2.cvtColor(nameplate_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)


            self.min_confidence = 50
            # height, width = gray.shape()
            # left, right = gray[:, :width//2 -400]

            # Extract text using OCR
            results = pytesseract.image_to_data(
                thresh, 
                output_type=pytesseract.Output.DICT,
                config=self.ocr_config_score
            )
            
            # Check each detected text piece
            for i in range(len(results['text'])):
                confidence = int(results['conf'][i])
                text = results['text'][i].strip().upper()
                
                if confidence > self.min_confidence and text:
                    # Check against target patterns
                    if self.check_score_patterns(text):
                        # Log detection to database
                        self.log_score_detection(text, confidence)
                        return True, text
            
            return False, None
            
        except Exception as e:
            print(f"SCORE detection error: {e}")
            return False, None


    def detect_player_in_region(self, nameplate_region):
        """Detect player in cropped region"""
        try:
            # Upscale the region first
            scale_factor = 3  # Experiment with different values (2-4 typically work well)
            height, width = nameplate_region.shape[:2]
            upscaled_region = cv2.resize(
                nameplate_region, 
                (width * scale_factor, height * scale_factor), 
                interpolation=cv2.INTER_CUBIC
            )

            # Preprocess image for better OCR
            gray = cv2.cvtColor(upscaled_region, cv2.COLOR_BGR2GRAY)
            # gray = cv2.cvtColor(nameplate_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            self.min_confidence = 50 

            # height, width = gray.shape()
            # left, right = gray[:, :width//2 -400]

            # Extract text using OCR
            results = pytesseract.image_to_data(
                thresh, 
                output_type=pytesseract.Output.DICT,
                config=self.ocr_config_player
            )
            
            # Check each detected text piece
            for i in range(len(results['text'])):
                confidence = int(results['conf'][i])
                text = results['text'][i].strip().upper()
                
                if confidence > self.min_confidence and text:
                    # Check against target patterns
                    if self.check_player_patterns(text):
                        # Log detection to database
                        self.log_player_detection(text, confidence)
                        return True, text
            
            return False, None
            
        except Exception as e:
            print(f"PLAYER detection error: {e}")
            return False, None






    def check_char_patterns(self, detected_text):
        """Check if detected text matches CHAR patterns"""
        cursor = self.conn_char.cursor()
        
        # Check for exact matches
        cursor.execute(
            'SELECT pattern FROM target_patterns WHERE pattern = ? AND active = 1',
            (detected_text,)
        )
        
        if cursor.fetchone():
            return True
        
        # Check if detected text contains any pattern
        cursor.execute('SELECT pattern FROM target_patterns WHERE active = 1')
        patterns = cursor.fetchall()
        
        for (pattern,) in patterns:
            if pattern in detected_text:
                return True
        
        return False





    def check_score_patterns(self, detected_text):
        """Check if detected text matches SCORE patterns"""
        cursor = self.conn_score.cursor()
        
        # Check for exact matches
        cursor.execute(
            'SELECT pattern FROM target_patterns WHERE pattern = ? AND active = 1',
            (detected_text,)
        )
        
        if cursor.fetchone():
            return True
        
        # Check if detected text contains any pattern
        cursor.execute('SELECT pattern FROM target_patterns WHERE active = 1')
        patterns = cursor.fetchall()
        
        for (pattern,) in patterns:
            if pattern in detected_text:
                return True
        
        return False



    def check_player_patterns(self, detected_text):
        """Check if detected text matches PLAYER patterns"""
        cursor = self.conn_player.cursor()
        
        # Check for exact matches
        cursor.execute(
            'SELECT pattern FROM target_patterns WHERE pattern = ? AND active = 1',
            (detected_text,)
        )
        
        if cursor.fetchone():
            return True
        
        # Check if detected text contains any pattern
        cursor.execute('SELECT pattern FROM target_patterns WHERE active = 1')
        patterns = cursor.fetchall()
        
        for (pattern,) in patterns:
            if pattern in detected_text:
                return True

        # for (pattern,) in patterns:
        #     # Single digit
        #     if len(pattern) == 1: 
        #         if detected_text == pattern:
        #             return True
        #     else:  # Multi-digit
        #         if pattern in detected_text:
        #             return True
        return False






    def log_char_detection(self, detected_text, confidence):
        """Log CHAR detection to database"""
        cursor = self.conn_char.cursor()
        
        cursor.execute('''
            INSERT INTO char_detections (timestamp, detected_text, confidence)
            VALUES (?, ?, ?)
        ''', (time.time(), detected_text, confidence))
        
        self.conn_char.commit()
        
        print(f"🔍 CHAR DETECTED: '{detected_text}' (confidence: {confidence}%)")



    def log_score_detection(self, detected_text, confidence):
        """Log SCORE detection to database"""
        cursor = self.conn_score.cursor()
        
        cursor.execute('''
            INSERT INTO score_detections (timestamp, detected_text, confidence)
            VALUES (?, ?, ?)
        ''', (time.time(), detected_text, confidence))
        
        self.conn_score.commit()
        
        print(f"🔍 SCORE DETECTED: '{detected_text}' (confidence: {confidence}%)")


    def log_player_detection(self, detected_text, confidence):
        """Log PLAYER detection to database"""
        cursor = self.conn_player.cursor()
        
        cursor.execute('''
            INSERT INTO score_detections (timestamp, detected_text, confidence)
            VALUES (?, ?, ?)
        ''', (time.time(), detected_text, confidence))
        
        self.conn_player.commit()
        
        print(f"🔍 PLAYER DETECTED: '{detected_text}' (confidence: {confidence}%)")




    def get_recent_char_detections(self, hours=24):
        """Get recent CHAR detections"""
        cursor = self.conn_char.cursor()
        
        since_time = time.time() - (hours * 3600)
        
        cursor.execute('''
            SELECT timestamp, detected_text, confidence
            FROM char_detections
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (since_time,))
        
        return cursor.fetchall()

    def get_recent_score_detections(self, hours=24):
        """Get recent SCORE detections"""
        cursor = self.conn_score.cursor()
        
        since_time = time.time() - (hours * 3600)
        
        cursor.execute('''
            SELECT timestamp, detected_text, confidence
            FROM score_detections
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (since_time,))
        
        return cursor.fetchall()


    def get_recent_player_detections(self, hours=24):
        """Get recent PLAYER detections"""
        cursor = self.conn_player.cursor()
        
        since_time = time.time() - (hours * 3600)
        
        cursor.execute('''
            SELECT timestamp, detected_text, confidence
            FROM score_detections
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (since_time,))
        
        return cursor.fetchall()



    def cleanup_databases(self):
        """Close both database connections"""
        if hasattr(self, 'conn_char'):
            self.conn_char.close()
        if hasattr(self, 'conn_score'):
            self.conn_score.close()
        if hasattr(self, 'conn_player'):
            self.conn_player.close()



#################################################################################################################
# NOTE: KEPT THIS HERE FOR FUTURE USE SINCE WE WILL NEED TO DETECT PLAYER NAMES AND PROBABLY TEAM NAMES AS WELL #
#################################################################################################################
# def setup_player_database(self):
#         """Setup player database"""
#         self.conn = sqlite3.connect('players.db')
#         cursor = self.conn.cursor()
#
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS players (
#                 id INTEGER PRIMARY KEY,
#                 name TEXT UNIQUE,
#                 team TEXT,
#                 position TEXT,
#                 active INTEGER DEFAULT 1
#             )
#         ''')
#
#         # Add sample players
#         players = [
#             ("LEBRON JAMES", "Lakers", "SF", 1),
#             ("STEPHEN CURRY", "Warriors", "PG", 1),
#             ("KEVIN DURANT", "Suns", "SF", 1),
#             ("GIANNIS ANTETOKOUNMPO", "Bucks", "PF", 1),
#             # Add more players...
#         ]
#
#         cursor.executemany(
#                 'INSERT OR IGNORE INTO players (name, team, position, active) VALUES (?, ?, ?, ?)',
#                 players
#         )
#         self.conn.commit()
#
#
#
#
#     def preprocess_nameplate(self, nameplate_region):
#         """Preprocess the nameplate region for better OCR"""
#         # Convert to grayscale
#         gray = cv2.cvtColor(nameplate_region, cv2.COLOR_BGR2GRAY)
#
#         # Apply thresholding to get better contrast
#         _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#
#         # Optional: Apply morphological operations to clean up
#         kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
#         cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
#
#         # Optional: Resize for better OCR (if text is too small)
#         height, width = cleaned.shape
#         if height < 50:  # If text is too small, scale it up
#             scale_factor = 50 / height
#             new_width = int(width * scale_factor)
#             new_height = int(height * scale_factor)
#             cleaned = cv2.resize(cleaned, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
#
#         return cleaned
#
#
#
#
#
#     def extract_text_from_nameplate(self, nameplate_region):
#         """Extract text directly from nameplate region using OCR"""
#         try:
#             # Preprocess the image
#             processed_region = self.preprocess_nameplate(nameplate_region)
#
#             # Perform OCR
#             results = pytesseract.image_to_data(
#                 processed_region, 
#                 output_type=pytesseract.Output.DICT,
#                 config=self.ocr_config
#             )
#
#             # Extract high-confidence text
#             detected_texts = []
#             for i in range(len(results['text'])):
#                 confidence = int(results['conf'][i])
#                 text = results['text'][i].strip()
#
#                 if confidence > self.min_confidence and len(text) > 1:
#                     detected_texts.append(text)
#
#             # Join all detected text pieces
#             full_text = ' '.join(detected_texts).upper()
#
#             return full_text if full_text else None
#
#         except Exception as e:
#             print(f"OCR Error: {e}")
#             return None
#
#
#
#
#
#     def check_player_database(self, detected_text):
#         """Check detected text against player database"""
#         if not detected_text:
#             return False, None
#
#         cursor = self.conn.cursor()
#
#         # Direct match first
#         cursor.execute(
#             'SELECT name, team, position FROM players WHERE name = ? AND active = 1', 
#             (detected_text,)
#         )
#
#         match = cursor.fetchone()
#         if match:
#             return True, {"name": match[0], "team": match[1], "position": match[2]}
#
#         # Fuzzy matching - check if detected text contains player name
#         cursor.execute(
#             'SELECT name, team, position FROM players WHERE ? LIKE "%" || name || "%" AND active = 1', 
#             (detected_text,)
#         )
#
#         match = cursor.fetchone()
#         if match:
#             return True, {"name": match[0], "team": match[1], "position": match[2]}
#
#         # Check if player name contains detected text
#         cursor.execute(
#             'SELECT name, team, position FROM players WHERE name LIKE "%" || ? || "%" AND active = 1', 
#             (detected_text,)
#         )
#
#         match = cursor.fetchone()
#         if match:
#             return True, {"name": match[0], "team": match[1], "position": match[2]}
#
#         return False, None
#
#
#
#
#
#     def detect_player_name(self, nameplate_region):
#         """Complete OCR-only pipeline for player detection"""
#         try:
#             # Extract text from nameplate
#             detected_text = self.extract_text_from_nameplate(nameplate_region)
#
#             if not detected_text:
#                 return False, None
#
#             # Avoid duplicate detections
#             current_time = time.time()
#             if (detected_text == self.last_detected_text and 
#                 current_time - self.last_detection_time < 2.0):  # 2 second cooldown
#                 return False, None
#
#             # Check against database
#             found, player_info = self.check_player_database(detected_text)
#
#             if found:
#                 self.last_detected_text = detected_text
#                 self.last_detection_time = current_time
#                 print(f"Detected text: '{detected_text}'")
#
#             return found, player_info
#
#         except Exception as e:
#             print(f"Player detection error: {e}")
#             return False, None
#
#




# class TextDetector:
#     def __init__(self):
#         # Model attributes
#         self.east_model_path = None
#
#         self.setup_player_database()
#
#         # Text detection paramters
#         self.text_confidenced = None
#         self.min_text_confidence = None
#
#
#
#     def setup_text_detection(self)
#         """Initialize EAST text detector"""
#         try:
#             self.east_model_path = "model\\frozen_east_text_detection.pb"
#         except Exception as e:
#             print(f'Model file not found or incorrect path. Check if model folder is set and model file exists.') 
#             sys.exit(1)
#
#         self.text_net = cv2.dnn.readNet(self.east_model_path)
#
#         self.text_confidece = 0.5
#         self.min_text_condifence = 60 # for OCR
#
#
#     def setup_player_database(self):
#         """Setup SQLite database with player names"""
#         self.conn = sqlite3.connect('players.db')
#         cursor = self.conn.cursor()
#
#         # Create players table
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS players (
#                 id INTEGER PRIMARY KEY,
#                 name TEXT UNIQUE,
#                 team TEXT,
#                 active INTEGER DEFAULT 1
#             )
#         ''')
#
#
#         # Add sample players
#         players = [
#                 (),
#                 (),
#                 (),
#         ]
#
#
#
#         cursor.executemany(
#                 'INSERT OR IGNORE INTO players (name, team, active) VALUES (?, ?, ?)',
#                 players
#         )
#
#         self.conn.commit()
#
#     def detect_text_in_region(self, cropped_region):
#         """Detect text in the cropped region"""
#         try:
#             # Resize image for EAST model (must be multiple of 32)
#             height, width = cropped_region.shape[:2]
#             new_width = int(width / 32) * 32
#             new_height = int(height / 32) * 32
#
#             if new_width == 0 or new_height == 0:
#                 return []
#
#             resized_region = cv2.resize(namplate_region, (new_width, new_height))
#
#             # Create blob and run EAST detection
#             blob = cv2.dnn.blobFromImage(
#                     resized_region, 1.0, (new_width, new_height),
#                     (123.68, 116.78, 103.94), swapRB=True, crop=False
#             )
#
#             # 123.68 = Mean pixel value for Blue channel across ImageNet dataset
#             # 116.78 = Mean pixel value for Green channel across ImageNet dataset
#             # 103.94 = Mean pixel value for Red channel across ImageNet dataset
#             # Why These Values Are UsedL:
#             # Mean subtraction is a common preprocessing step in deep learning:
#             # Normalization: Centers the data around zero by subtracting the mean
#             # Standardization: Helps the model converge faster during training
#             # Consistency: The EAST model was trained with these same mean values
#
#
#             # Set input to the network
#             self.east_net.setInput(blob)
#             scores, geometry = self.east_ner.forward(
#                     [
#                         "feature_fusion/Conv_7/Sigmoid",
#                         "feature_fusion/concat_3"
#                     ]
#             )
#
#             # Decode predictions (simplified)
#             text_regions = self.decode_predictions(scores, geometry, width, height)
#             return text_regions
#
#
#
#
#         def extract_text_from_regions(self, image, text_regions):
#             """ Extract text content using OCR"""
#             detected_texts = []
#
#             for (x, y, w, h) in text_regions:
#                 text_region = image[y:y+h, x:x+w]
#
#                 # OCR extraction
#                 try:
#                     text = pytesseract.image_to_string(text_region, config='--psm 8').strip()
#                     if text and len(text) > 2:
#                         detected_texts.append(text)
#                 except:
#                     continue
#
#             return detected_texts
#
#
#
#         def check_player_database(self, detected_texts):
#             """ Check against player database"""
#             cursor = self.conn.cursor()
#
#             for text in detected_texts:
#                 #Fuzzy matching (NOTE: check libraries like fuzzywuzzy)
#                 cursor.execute(
#                         'SELECT name, team FROM players WHERE name LIKE ? AND active = 1',
#                         (f'%{text}%',)
#                 )
#
#                 matches = cursor.fetchall()
#                 if matches:
#                     return True, matches[0] # Return first match
#
#             return False, None
#
#         def detect_player_names(self, cropped_region):
#             """Complete pipeline: EAST > OCR > Database check"""
#
#             try:
#                 # Detect text regions
#                 text_regions = self.detect_text_regions(cropped_region)
#
#                 if not text_regions:
#                     return False, None
#
#                 # Extract text content
#                 detected_texts = self.extract_text_from_regions(cropped_region, text_regions)
#
#                 if not detected_texts:
#                     return False, None
#
#                 # Check against database
#                 found, player_info = self.check_player_database(decoded_texts)
#
#                 return found, player_info
#
#             except Exception as e:
#                 print(f"Error in player detection: {e}")
#                 return False, None
#
#         def decode_predictions(self, scores, geometry, orig_width, orig_height):
#             """Simplified prediction decoding"""
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
