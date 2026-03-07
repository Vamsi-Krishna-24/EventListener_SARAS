# listener.py
# Core event listener for SARAS - Word Lookup App
# Optimized and merged from main.py, main1.py, main2.py

import time
import threading
import queue
import pyperclip
from pynput import mouse, keyboard


class ListenerController:
    """
    Listens for global double-clicks, copies the selected word,
    and puts it into a queue for the main app thread to process.

    Using a queue (from main1.py) keeps the listener completely
    decoupled from the UI — the listener never touches popups directly.
    """

    DOUBLE_CLICK_THRESHOLD = 0.3  # seconds between clicks to count as double-click
    CLIPBOARD_WAIT = 0.25          # seconds to wait after Ctrl+C for clipboard to update

    def __init__(self, word_queue: queue.Queue):
        self._kbd = keyboard.Controller()
        self._last_click_time: float | None = None
        self._listener: mouse.Listener | None = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()       # prevent race condition on last_click_time
        self.word_queue = word_queue

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start the mouse listener in a background thread."""
        if self._listener and self._listener.running:
            print("[WARN] Listener already running.")
            return
        print("[INFO] Starting listener...")
        self._stop_flag.clear()
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()

    def stop(self):
        """Cleanly stop the mouse listener."""
        print("[INFO] Stopping listener...")
        self._stop_flag.set()
        if self._listener:
            self._listener.stop()
            self._listener = None

    def is_running(self) -> bool:
        return self._listener is not None and self._listener.running

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _on_click(self, x, y, button, pressed):
        # Only act on LEFT button RELEASE (more reliable for double-click detection)
        if button != mouse.Button.left or pressed:
            return

        # If we've been asked to stop, bail out
        if self._stop_flag.is_set():
            return

        current_time = time.time()

        with self._lock:
            last = self._last_click_time
            self._last_click_time = current_time

        if last and (current_time - last) < self.DOUBLE_CLICK_THRESHOLD:
            self._handle_double_click()

    def _simulate_ctrl_c(self):
        """Simulate Ctrl+C to copy currently selected text."""
        self._kbd.press(keyboard.Key.ctrl)
        self._kbd.press('c')
        self._kbd.release('c')
        self._kbd.release(keyboard.Key.ctrl)

    def _handle_double_click(self):
        """Copy selected text and push the word into the queue."""
        self._simulate_ctrl_c()
        time.sleep(self.CLIPBOARD_WAIT)

        copied_text = pyperclip.paste().strip()

        if not copied_text:
            print("[LOG] Double-click detected but clipboard is empty.")
            return

        # Only pass single words — skip if user selected a sentence
        if len(copied_text.split()) > 5:
            print(f"[LOG] Skipping — too many words selected: '{copied_text[:40]}'")
            return

        print(f"[LOG] Word captured: '{copied_text}'")
        self.word_queue.put(copied_text)