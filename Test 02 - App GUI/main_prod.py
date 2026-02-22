# main2.py

import sys
import time
import signal
import threading
import queue
import pyperclip
from pynput import mouse, keyboard
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer
from db_handler import get_word_meaning
from popup import Popup

# ------------------------------------------------------------------ #
#  Icons
#  lotus_coin_v2.ico      — default / loading state
#  lotus_running_green.ico — listener ON
#  lotus_sleeping_red.ico  — listener OFF
# ------------------------------------------------------------------ #

ICON_DEFAULT = "lotus_coin_v2.ico"
ICON_ON      = "lotus_running_green.ico"
ICON_OFF     = "lotus_sleeping_red.ico"

# ------------------------------------------------------------------ #
#  App Setup                                                           #
# ------------------------------------------------------------------ #

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

word_queue = queue.Queue()
active_popups = []


# ------------------------------------------------------------------ #
#  Listener                                                            #
# ------------------------------------------------------------------ #

class ListenerController:
    def __init__(self):
        self.kbd = keyboard.Controller()
        self.last_click_time = None
        self.listener = None
        self._stop_flag = threading.Event()

    def on_click(self, x, y, button, pressed):
        if pressed or self._stop_flag.is_set():
            return

        if button == mouse.Button.left:
            current_time = time.time()
            if self.last_click_time and (current_time - self.last_click_time) < 0.3:
                self.simulate_ctrl_c()
                time.sleep(0.3)
                copied_text = pyperclip.paste().strip()
                print(f"[LOG] Copied Text: {copied_text}")
                if copied_text:
                    word_queue.put(copied_text)
            self.last_click_time = current_time

    def simulate_ctrl_c(self):
        self.kbd.press(keyboard.Key.ctrl)
        self.kbd.press('c')
        self.kbd.release('c')
        self.kbd.release(keyboard.Key.ctrl)

    def start(self):
        if not self.listener or not self.listener.running:
            print("[INFO] Listener started.")
            self._stop_flag.clear()
            self.listener = mouse.Listener(on_click=self.on_click)
            self.listener.start()

    def stop(self):
        print("[INFO] Listener stopped.")
        self._stop_flag.set()
        if self.listener:
            self.listener.stop()
            self.listener = None


# ------------------------------------------------------------------ #
#  Tray Icon                                                           #
# ------------------------------------------------------------------ #

class TrayIcon(QSystemTrayIcon):
    def __init__(self, controller: ListenerController):
        super().__init__()
        self.controller = controller
        self.is_active = True

        self.setIcon(QIcon(ICON_ON))
        self.setToolTip("SARAS — Active")

        self.menu = QMenu()

        self.toggle_action = QAction("⏸  Turn Off")
        self.toggle_action.triggered.connect(self.toggle)
        self.menu.addAction(self.toggle_action)

        self.menu.addSeparator()

        quit_action = QAction("✕  Quit SARAS")
        quit_action.triggered.connect(shutdown)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)
        self.activated.connect(self.on_tray_click)

        self.show()
        self.showMessage(
            "SARAS",
            "Running in background. Double-click any word to look it up.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def toggle(self):
        if self.is_active:
            self.controller.stop()
            self.is_active = False
            self.toggle_action.setText("▶  Turn On")
            self.setIcon(QIcon(ICON_OFF))
            self.setToolTip("SARAS — Paused")
            self.showMessage("SARAS", "Turned OFF.", QSystemTrayIcon.MessageIcon.Information, 2000)
            print("[INFO] SARAS toggled OFF.")
        else:
            self.controller.start()
            self.is_active = True
            self.toggle_action.setText("⏸  Turn Off")
            self.setIcon(QIcon(ICON_ON))
            self.setToolTip("SARAS — Active")
            self.showMessage("SARAS", "Turned ON.", QSystemTrayIcon.MessageIcon.Information, 2000)
            print("[INFO] SARAS toggled ON.")

    def on_tray_click(self, reason):
        # Left single click = toggle
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle()


# ------------------------------------------------------------------ #
#  Queue Processor                                                     #
# ------------------------------------------------------------------ #

def process_queue():
    while not word_queue.empty():
        try:
            word = word_queue.get_nowait()
        except queue.Empty:
            break

        result = get_word_meaning(word)
        if result:
            popup = Popup(
                word,
                result.get("definition", ""),
                ", ".join(result.get("examples", [])),
                ", ".join(result.get("synonyms", []))
            )
        else:
            popup = Popup(word, "Word not found in database.", "", "")

        popup.show()
        popup.raise_()
        popup.activateWindow()
        active_popups.append(popup)
        active_popups[:] = [p for p in active_popups if p.isVisible()]


# ------------------------------------------------------------------ #
#  Clean Shutdown                                                      #
# ------------------------------------------------------------------ #

def shutdown(*args):
    print("[INFO] Shutting down cleanly...")
    controller.stop()
    timer.stop()
    signal_timer.stop()
    app.quit()

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


# ------------------------------------------------------------------ #
#  Entry Point                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    controller = ListenerController()
    controller.start()

    tray = TrayIcon(controller)

    timer = QTimer()
    timer.timeout.connect(process_queue)
    timer.start(100)

    # Allows Python to process SIGINT even while Qt event loop is running
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(200)

    app.exec()