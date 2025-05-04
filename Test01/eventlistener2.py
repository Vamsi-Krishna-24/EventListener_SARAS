import pyperclip
import time, win32api, win32con
from pynput import mouse, keyboard

kbd = keyboard.Controller()

def on_click(x, y, button, pressed):
    if button == mouse.Button.left and not pressed:  # This means mouse button was released
        if on_click.last_click_time and time.time() - on_click.last_click_time < 0.3:
            # Perform the action once double-click is detected
            kbd.press(keyboard.Key.ctrl)
            kbd.press('c')
            kbd.release('c')
            kbd.release(keyboard.Key.ctrl)
            time.sleep(0.3)
            copied_text = pyperclip.paste()
            print("Copied word:", copied_text)
        
        on_click.last_click_time = time.time()

on_click.last_click_time = None

with mouse.Listener(on_click=on_click) as listener:
    listener.join()
