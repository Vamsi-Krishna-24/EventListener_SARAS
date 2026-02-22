import time
import win32api
import win32con
import pyperclip
import keyboard

def tap_and_select(x, y):
    # Move cursor to position
    win32api.SetCursorPos((x, y))
    time.sleep(0.1)  # Give time for cursor to arrive
    
    # First click
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
    
    # Very short delay between clicks (crucial for double-click recognition)
    time.sleep(0.05)  # Typically 0.05-0.1 seconds works well
    
    # Second click
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    keyboard.press_and_release('ctrl+c')
    time.sleep(0.1)

    copied_text = pyperclip.paste()
    return copied_text

# Example usage
copied_text = tap_and_select(405,120)
print("copied word:",copied_text)