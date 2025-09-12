Prototype program written in Python, using the PyAV(FFmpeg) and OCR (Tesseract) libraries. This was built to detect text or frame data of a given region coordinate, from a video input stream (window capture or video file), and trigger automatic frame recording into an output file of any given format. 

More detailed information about use cases will be added soon but I can provide a simple example:

- Imagine I want to play a sports broadcast on my desktop using either a browser or a media player and I want my program to start recording the content whenever a specific event is shown on the screen, for example, every time the scoreboard of a football game is displayed on a certain position (which will be inspected frame by frame). 

- This program will collect the window coordinates of the given window title name which will then get captured to a video input stream.

- We can then select a specific region of that captured input stream and inspect its the pixel count, frame by frame, to detect if a change occurred.

- We can also use the text recognition feature to detect given words/names/sequences of characters on the frame.

- These detections will then trigger the program to record the input stream content immediately to the designated output stream (to be generated file) whenever the inspected frame region pixel count is within the given min/max threshold or whenever a specified piece of text is detected. 


******************************************************************************************

*Implemented features*:


- Text recognition logic using OCR

- Circular buffer logic in order to record last x seconds of the captured input whenever the detection is triggered (sort of an *Instant Replay* but with more custom options to manipulate).

- Possibility to merge all the generated output files into a single edited video, with different aesthetic possibilities. This is the main idea and goal of the whole thing. I want the captured video segments to be automatically edited with pre defined aesthetic options, behaving like an automated video editing tool.

******************************************************************************************


