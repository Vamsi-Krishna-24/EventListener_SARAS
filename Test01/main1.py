# trigger.py

import pyperclip
import time
from pynput import mouse, keyboard

kbd = keyboard.Controller()

def start_listener(word_queue):
    def on_click(x, y, button, pressed):
        if button == mouse.Button.left and not pressed:
            if on_click.last_click_time and time.time() - on_click.last_click_time < 0.3:
                # Detected double-click
                kbd.press(keyboard.Key.ctrl)
                kbd.press('c')
                kbd.release('c')
                kbd.release(keyboard.Key.ctrl)
                time.sleep(0.2)
                copied_text = pyperclip.paste().strip()
                print(f"[trigger] Copied word: {copied_text}")
                if copied_text:
                    word_queue.put(copied_text)

            on_click.last_click_time = time.time()

    on_click.last_click_time = None
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()
