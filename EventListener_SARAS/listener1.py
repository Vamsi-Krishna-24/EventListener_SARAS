# listener1.py
# SARAS event listener

import time
import threading
import queue
import pyperclip
from pynput import mouse, keyboard


class ListenerController:

    DOUBLE_CLICK_THRESHOLD = 0.30
    LONG_PRESS_THRESHOLD   = 0.55
    CLIPBOARD_WAIT         = 0.20

    def __init__(self, word_queue: queue.Queue, trigger_mode="double_click"):

        self.word_queue   = word_queue
        self.trigger_mode = trigger_mode

        self._kbd   = keyboard.Controller()
        self._mouse = mouse.Controller()

        self._listener = None

        self._last_click_time = None
        self._press_time      = None

        self._stop_flag = threading.Event()
        self._lock      = threading.Lock()

    # ------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------

    def start(self):
        if self._listener and self._listener.running:
            return
        self._stop_flag.clear()
        print(f"[INFO] Listener started ({self.trigger_mode})")
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()

    def stop(self):
        print("[INFO] Listener stopped")
        self._stop_flag.set()
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_trigger_mode(self, mode: str):
        """Switch mode live — no restart needed."""
        if mode not in ("double_click", "long_press"):
            print(f"[WARN] Unknown trigger mode: {mode}")
            return
        self.trigger_mode  = mode
        # reset state so no phantom presses carry over
        self._last_click_time = None
        self._press_time      = None
        print(f"[INFO] Trigger mode → {mode}")

    def is_running(self) -> bool:
        return self._listener is not None and self._listener.running

    # ------------------------------------------------
    # MAIN CLICK HANDLER
    # ------------------------------------------------

    def _on_click(self, x, y, button, pressed):

        if button != mouse.Button.left:
            return

        if self._stop_flag.is_set():
            return

        if self.trigger_mode == "double_click":
            self._handle_double_click(pressed)

        elif self.trigger_mode == "long_press":
            self._handle_long_press(pressed)

    # ------------------------------------------------
    # DOUBLE CLICK
    # ------------------------------------------------

    def _handle_double_click(self, pressed):

        if pressed:
            return

        current_time = time.time()

        with self._lock:
            last = self._last_click_time
            self._last_click_time = current_time

        if last and (current_time - last) < self.DOUBLE_CLICK_THRESHOLD:
            self._capture_word()

    # ------------------------------------------------
    # LONG PRESS
    # ------------------------------------------------

    def _handle_long_press(self, pressed):

        if pressed:
            self._press_time = time.time()

        else:
            if not self._press_time:
                return

            duration = time.time() - self._press_time
            self._press_time = None

            if duration >= self.LONG_PRESS_THRESHOLD:
                print(f"[LOG] Long press detected ({duration:.2f}s)")

                # Run capture in a thread so we don't block the listener callback.
                # If we block here, the simulated double-click fires its own
                # on_click callbacks back into this same method — causing a loop.
                threading.Thread(target=self._long_press_capture, daemon=True).start()

    def _long_press_capture(self):
        """Runs off the listener thread to avoid re-entrant on_click calls."""
        # Briefly pause the listener so the simulated double-click
        # doesn't trigger another long press detection
        self._stop_flag.set()

        try:
            self._mouse.click(mouse.Button.left, 2)
            time.sleep(0.08)
            self._capture_word()
        finally:
            # Re-arm the listener
            self._stop_flag.clear()

    # ------------------------------------------------
    # WORD CAPTURE
    # ------------------------------------------------

    def _simulate_ctrl_c(self):
        self._kbd.press(keyboard.Key.ctrl)
        self._kbd.press('c')
        self._kbd.release('c')
        self._kbd.release(keyboard.Key.ctrl)

    def _capture_word(self):

        self._simulate_ctrl_c()
        time.sleep(self.CLIPBOARD_WAIT)

        text = pyperclip.paste().strip()

        if not text:
            print("[LOG] Clipboard empty")
            return

        if len(text.split()) > 5:
            print("[LOG] Too many words, ignoring")
            return

        print(f"[LOG] Word captured: {text}")
        self.word_queue.put(text)