# main.py

import threading
import queue
import time

from trigger import start_listener  # you’ll modify trigger.py to include this
from db_handler import get_word_meaning
from popup import show_popup  # assumes popup.py has a show_popup(dict) function

# Create a queue to receive words from the trigger
word_queue = queue.Queue()

def process_words():
    """ Continuously process words sent from the trigger module """
    while True:
        word = word_queue.get()  # Blocks until a word is received
        print(f"[main] Received word: {word}")

        meaning_data = get_word_meaning(word)

        if meaning_data:
            print(f"[main] Found meaning for {word}")
            show_popup(meaning_data)
        else:
            print(f"[main] Word '{word}' not found in DB.")

        time.sleep(0.5)  # Prevent rapid fire

if __name__ == "__main__":
    # Start the mouse trigger listener in a separate thread
    listener_thread = threading.Thread(target=start_listener, args=(word_queue,))
    listener_thread.daemon = True  # Dies with main program
    listener_thread.start()

    print("[main] Listener started. Waiting for double-tap selections...")

    # Start the processing loop
    process_words()
