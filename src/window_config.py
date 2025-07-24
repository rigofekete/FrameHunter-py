import sys

import win32gui
import win32con
import ctypes

import global_vars
from global_vars import ( 
        PCSX2, PES2, WE6, WE6FE,
        ERROR, START, SUCCESS
)

def get_dpi_aware_window_rect(window):
    print(f'{START} Initializing window: {window}...')
    try:
        hwnd = win32gui.FindWindow(None, window)
        if not hwnd:
            print("Window not found")

        # NOTE: Windows does not allow foreground call if window is shown and behind other windows
        # Because of this we need to force minimize and restore to be able to call it without errors...
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        # time.sleep(0.1)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f'Error in get_dpi_aware_window_rect(): {e}')
        return None
        # TODO go back to the main menu after exception and don't exit the program 
        sys.exit(1)
    
    # Get window rect values from the OS (in physical pixels)
    rect = win32gui.GetWindowRect(hwnd)
    x, y, r, b = rect
    width = r - x
    height = b - y

    # Get DPI for the window using Windows API
    try:
        # Windows 10+ (1607+) method
        user32 = ctypes.windll.user32
        dpi = user32.GetDpiForWindow(hwnd)
    except AttributeError:
        print("user32 and dpi value returns with ctypes failed")
        # Fallback to standard DPI


    #### DPI SCALE CALCULATION
    # scale = dpi / 96.0: Calculates the DPI scaling factor. Since 96 DPI is the Windows standard baseline:
    # 96 DPI = 1.0 scale (100% scaling)
    # 120 DPI = 1.25 scale (125% scaling)
    # 144 DPI = 1.5 scale (150% scaling)
    # 192 DPI = 2.0 scale (200% scaling)

    global_vars.DPI = dpi / 96.0


    x = int(x * global_vars.DPI) + 10             # add/sub values to fine-tune capturing x, y, w, h regions
    y = int(y * global_vars.DPI) + 20             # add/sub values to fine-tune capturing x, y, w, h regions
    width = int(width * global_vars.DPI) - 20     # add/sub values to fine-tune capturing x, y, w, h regions
    height = int(height * global_vars.DPI) -20    # add/sub values to fine-tune capturing x, y, w, h regions

    # we need to make sure that the w and h values are even! 
    # (libx264 requires width/height divisible by 2)
    width = width - (width % 2)
    height = height - (height % 2)
    return (x, y, x + width, y + height)



def crop_regions(window): 
    # Crop the region of the player name (bottom center) of PES2
    # NOTE: Remember that when we crop the captured frame we are dealing with the new frame coord system,
    # starting at 0,0 and not the desktop coordinates which were only needed to frame the capture area
    # TODO: Because of that, lets think if there is any need to have global variables for x,y,w,h

    if window == PES2:
        # Complete nameplate region
        x_nameplate = 930
        y_nameplate = 1820

        width_nameplate = global_vars.WIDTH // 2 - 1110 
        # height_nameplate = global_vars.HEIGHT // 10 - 140 
        height_nameplate = global_vars.HEIGHT // 2 - 980
        # always make sure values are even!
        width_nameplate = width_nameplate - (width_nameplate % 2)
        height_nameplate = height_nameplate - (height_nameplate % 2)

        ####################
        # Min. Goal region #
        ####################
        
        x_min = global_vars.WIDTH // 2 + 50
        y_min = 320 
        width_min = global_vars.WIDTH // 2 - 1090   
        height_min = global_vars.HEIGHT // 2 - 950  

        # always make sure values are even!
        width_min = width_min - (width_min % 2)
        height_min = height_min - (height_min % 2)

        ###########################
        # Goal Scorer Player Name #
        ###########################

        x_name = global_vars.WIDTH // 2 - 390
        y_name = global_vars.HEIGHT - 380

        width_name = global_vars.WIDTH // 6  
        height_name = global_vars.HEIGHT // 10 - 120 

        # always make sure values are even!
        width_name = width_name - (width_name % 2)
        height_name = height_name - (height_name % 2)

    elif window == WE6:

        # Complete nameplate region
        x_nameplate = 930
        y_nameplate = 1820

        width_nameplate = global_vars.WIDTH // 2 - 1110 
        # height_nameplate = global_vars.HEIGHT // 10 - 140 
        height_nameplate = global_vars.HEIGHT // 2 - 980
        # always make sure values are even!
        width_nameplate = width_nameplate - (width_nameplate % 2)
        height_nameplate = height_nameplate - (height_nameplate % 2)

        ####################
        # Min. Goal region #
        ####################
        
        x_min = global_vars.WIDTH // 2 + 50
        y_min = 320 
        width_min = global_vars.WIDTH // 2 - 1090   
        height_min = global_vars.HEIGHT // 2 - 950  

        # always make sure values are even!
        width_min = width_min - (width_min % 2)
        height_min = height_min - (height_min % 2)

        ###########################
        # Goal Scorer Player Name #
        ###########################

        x_name = global_vars.WIDTH // 2 - 390
        y_name = global_vars.HEIGHT - 380

        width_name = global_vars.WIDTH // 6  
        height_name = global_vars.HEIGHT // 10 - 120 

        # always make sure values are even!
        width_name = width_name - (width_name % 2)
        height_name = height_name - (height_name % 2)

    return [
        {
            'name': 'nameplate',
            'x': x_nameplate, 
            'y': y_nameplate, 
            'width': width_nameplate, 
            'height': height_nameplate
        },
        {
            'name': 'min_region',
            'x': x_min, 
            'y': y_min, 
            'width': width_min, 
            'height': height_min
        },
        {
            'name': 'name_region',
            'x': x_name, 
            'y': y_name, 
            'width': width_name, 
            'height': height_name
        },
    ]

