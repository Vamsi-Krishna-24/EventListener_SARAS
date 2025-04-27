import pyperclip
import time, win32api, win32con
from pynput import mouse, keyboard

kbd = keyboard.Controller()

def on_click(x,y,button,pressed):
    if pressed and button==mouse.Button.left:
        if on_click.last_click_time and time.time()-on_click.last_click_time <0.3:

            kbd.press(keyboard.Key.ctrl)
            kbd.press('c')
            kbd.release('c')
            kbd.release(keyboard.Key.ctrl)
            time.sleep(0.3)
            copied_text = pyperclip.paste()
            print("Copied word",copied_text)
            print(on_click.last_click_time)
            print(time.time()-on_click.last_click_time)
        on_click.last_click_time=time.time()

on_click.last_click_time = None

with mouse.Listener(on_click=on_click) as listener:
    listener.join()
    listener.stop()


#the problem is triple click and fourth click and so on....They are dupliating  !!
# triggering the double-click logic multiple times because the time difference between clicks is still within the threshold 


## Adding cool down period, basically a temporary lock!
## ensures we don’t keep detecting double-clicks on every click after the initial one