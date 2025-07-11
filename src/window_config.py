import sys

import win32gui
import win32con
import ctypes

import global_vars



def get_dpi_aware_window_rect(title):
    try:
        hwnd = win32gui.FindWindow(None, title)
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

    scale = dpi / 96.0


    x = int(x * scale) + 10             # add/sub values to fine-tune capturing x, y, w, h regions
    y = int(y * scale) + 20             # add/sub values to fine-tune capturing x, y, w, h regions
    width = int(width * scale) - 20     # add/sub values to fine-tune capturing x, y, w, h regions
    height = int(height * scale) -20    # add/sub values to fine-tune capturing x, y, w, h regions

    # we need to make sure that the w and h values are even! 
    # (libx264 requires width/height divisible by 2)
    width = width - (width % 2)
    height = height - (height % 2)

    return (x, y, x + width, y + height)



def crop_regions(): 
    # TODO: IMPORTANT, handle errors for specific situations where the given coordinates
    # go beyond the available display margins
    # Crop the region of the player name (bottom center) of PES2
    x_nameplate = global_vars.X - 10 
    y_nameplate = global_vars.Y + 1795
    # x_nameplate = X + 40    
    # y_nameplate = Y + 1795
    width_nameplate = global_vars.WIDTH // 2  - 1122
    height_nameplate = global_vars.HEIGHT // 2 - 980  

    # always make sure values are even!
    width_nameplate = width_nameplate - (width_nameplate % 2)
    height_nameplate = height_nameplate - (height_nameplate % 2)

    return [
        {
            'name': 'nameplate',
            'x': x_nameplate, 
            'y': y_nameplate, 
            'width': width_nameplate, 
            'height': height_nameplate
        }
    ]
