import pyperclip
import time
from pynput import mouse, keyboard

kbd = keyboard.Controller()

def on_click(x,y,button,pressed):
    if pressed and button==mouse.Button.left:
        if on_click.last_click_time and time.time()-on_click.last_click_time <0.1:

            kbd.press(keyboard.Key.ctrl)
            kbd.press('c')
            kbd.release('c')
            kbd.release(keyboard.Key.ctrl)
            time.sleep(0.1)
            copied_text = pyperclip.paste()
            print("Copied word",copied_text)
        on_click.last_click_time=time.time()

on_click.last_click_time = None

with mouse.Listener(on_click=on_click) as listener:
    listener.join()