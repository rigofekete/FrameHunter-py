Prototype program written in Python, using the PyAV(FFmpeg) lib, built to detect given region coordinates from a video input stream (window capture or video file) in order to trigger automatic frame recording into an output file of any given format. 

More detailed information about use cases will be added soon but I can provide a simple example:

- Imagine I want to play a sports video on my desktop using either a browser or a media player and I want my program to start recording the content whenever a specific event is shown on the screen, for example, every time the scoreboard of a football game is displayed on a certain position (which will be inspected frame by frame). 

- This program will collect the window coordinates of the given window title name which will then get captured to a video input stream.

- We can then select a specific region of that captured input stream and inspect its the pixel count, frame by frame, to detect if a change occurred. 

- That change will then trigger the program to record the input stream content immediately to the designated output stream (to be generated file) whenever the inspected frame region pixel count is within the given min/max threshold. 

******************************************************************************************

I am planning to add a more visual example, using screenshots, to explain how this is behaving more explicitly. 

Future plans:

* Rewrite the whole program in C for proper performance and execution 
* Circular buffer logic in order to record last x seconds of the captured input whenever the detection is triggered (sort of an *Instant Replay* but with more custom options to manipulate).
* Possibility to merge all the generated output files into a single edited video, with different aesthetic possibilities. This is the main idea and goal of the whole thing. I want the captured video segments to be automatically edited with pre defined aesthetic options, behaving like an automated video editing tool.
* Text detection
* Set up instructions and requirements.txt