# FrameHunter-py

**Event-driven video capture and auto-editing with OCR and frame-diff (Python, PyAV/FFmpeg, Tesseract)**

---

## 📌 Description
A Python tool that watches a video/window stream, detects on-screen events via OCR or pixel-change in a defined region, and instantly records clips—optionally merging them into a styled final edit.

---

## 📖 Overview
FrameHunter-py monitors a window or file input, inspects a target region frame-by-frame, and triggers recording when thresholds are met (pixel-diff) or specified text is detected (OCR).  
It uses a circular buffer to capture the previous **N seconds** for instant replay-style clips.  
Finally, it can batch-merge generated clips into a single video with predefined aesthetic options for automated editing workflows.

---

## ✨ Key Features
- 📝 **OCR-based text/event detection** (Tesseract)  
- 🎞️ **Region-based pixel-change detection** with min/max thresholds  
- ⏮️ **Circular buffer** to record last *N* seconds on trigger  
- 📦 **Output to common formats** via PyAV/FFmpeg  
- 🎨 **Optional post-processing**: merge clips with styling presets  

---

## 💡 Example Use Case
Record every scoreboard change or player name appearance during a live sports stream by watching a fixed screen region.  
Detected events automatically produce clips and compile into a highlight reel.

---

## 🚀 Quickstart (Windows PowerShell / Command Prompt)

1. **Clone the repository**
   ```powershell
   git clone https://github.com/your-username/py-ReCap.git
   cd py-ReCap
   ```

2. **Set up a Python virtual environment** (recommended)
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the program**
   ```powershell
   run
   ```


✅ The program will start monitoring according to your configuration (regions, OCR patterns, thresholds, etc.).  
You can edit these values in the src\window_config.py and src\text_detection.py files. 




