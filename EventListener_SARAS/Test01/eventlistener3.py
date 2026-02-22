# main.py

import time
import pyperclip
from pynput import mouse, keyboard
from db_handler import get_word_meaning
from popup import show_popup

# Create keyboard controller to simulate Ctrl+C
kbd = keyboard.Controller()

# Track last click time
last_click_time = None

def on_click(x, y, button, pressed):
    global last_click_time

    # Detect left-button release (not press)
    if button == mouse.Button.left and not pressed:
        current_time = time.time()
        if last_click_time and (current_time - last_click_time) < 0.3:
            # Double-tap detected
            # Simulate Ctrl+C to copy selected word
            kbd.press(keyboard.Key.ctrl)
            kbd.press('c')
            kbd.release('c')
            kbd.release(keyboard.Key.ctrl)

            time.sleep(0.3)  # Give system time to copy text

            copied_text = pyperclip.paste().strip()
            print(f"[LOG] Copied Text: {copied_text}")

            if copied_text:
                result = get_word_meaning(copied_text)
                if result:
                    show_popup(
                        copied_text,
                        result.get("definition", ""),
                        ", ".join(result.get("examples", [])),
                        ", ".join(result.get("synonyms", []))
                    )
                else:
                    show_popup(copied_text, "Word not found in database.", "", "")
        last_click_time = current_time

def listen_double_click():
    print("[INFO] Listening for double-clicks...")
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()  # Keeps running in background

if __name__ == "__main__":
    listen_double_click()
