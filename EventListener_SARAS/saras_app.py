"""
Saras — Single Entry Point  |  PyQt6  |  v0.1
══════════════════════════════════════════════════════════════════
  THIS IS THE ONLY FILE YOU NEED TO RUN.
  Delete (or ignore) main_prod.py — it is fully replaced by this.

  The tray icon and the in-app toggle are both wired to AppState.
  Toggling either one instantly updates the other.
══════════════════════════════════════════════════════════════════
"""

import sys
import os
import time
import signal
import threading
import queue
import urllib.parse
import webbrowser

print("[SARAS] Starting...", flush=True)

import pyperclip
from pynput import mouse, keyboard

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QCheckBox,
    QComboBox, QStackedWidget, QGraphicsDropShadowEffect,
    QTextEdit, QLayout, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QObject, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QIcon, QCursor, QPixmap, QPainter, QPen, QAction

from db_handler import get_word_meaning
from popup import Popup

print("[SARAS] Imports OK", flush=True)


# ===============================================================
# THEME
# ===============================================================
class Theme:
    BG           = "#FAF8F5"
    SURFACE      = "#FFFFFF"
    CARD         = "#F5F2ED"
    BORDER       = "#E8E2D9"
    ACCENT       = "#2D2926"
    ACCENT_SOFT  = "#6B5E52"
    TEXT         = "#1A1612"
    TEXT_SUB     = "#8C7B6E"
    TEXT_MUTED   = "#B5A99D"
    HIGHLIGHT    = "#C9A96E"
    HIGHLIGHT_LT = "#F0E6D3"
    DANGER       = "#C0392B"
    SUCCESS      = "#27AE60"
    RADIUS       = "10px"
    RADIUS_LG    = "14px"


# ===============================================================
# SHARED STATE  — created after QApplication, drives everything
# ===============================================================
class AppState(QObject):
    """
    Single source of truth for on/off.
    STATE.toggled(bool) is emitted on every change.
    ListenerController subscribes to this — so does every UI widget.
    """
    toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._active = True

    @property
    def active(self):
        return self._active

    def set_active(self, val):
        if val == self._active:
            return
        self._active = val
        self.toggled.emit(val)

    def toggle(self):
        self.set_active(not self._active)


STATE = None  # assigned in main() after QApplication exists


# ===============================================================
# LISTENER CONTROLLER  (from main_prod.py, wired to STATE)
# ===============================================================
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
            now = time.time()
            if self.last_click_time and (now - self.last_click_time) < 0.3:
                self.simulate_ctrl_c()
                time.sleep(0.3)
                copied = pyperclip.paste().strip()
                print(f"[LOG] Copied: {copied}", flush=True)
                if copied:
                    word_queue.put(copied)
            self.last_click_time = now

    def simulate_ctrl_c(self):
        self.kbd.press(keyboard.Key.ctrl)
        self.kbd.press('c')
        self.kbd.release('c')
        self.kbd.release(keyboard.Key.ctrl)

    def start(self):
        if not self.listener or not self.listener.running:
            print("[INFO] Listener started.", flush=True)
            self._stop_flag.clear()
            self.listener = mouse.Listener(on_click=self.on_click)
            self.listener.start()

    def stop(self):
        print("[INFO] Listener stopped.", flush=True)
        self._stop_flag.set()
        if self.listener:
            self.listener.stop()
            self.listener = None


word_queue = queue.Queue()
active_popups = []


def process_queue():
    """Called every 100ms by QTimer — pops words from queue and shows popups."""
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
        popup.show(); popup.raise_(); popup.activateWindow()
        active_popups.append(popup)
        active_popups[:] = [p for p in active_popups if p.isVisible()]


# ===============================================================
# ICON HELPERS
# ===============================================================
_BASE   = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_BASE)


def _find_icon(filename):
    for folder in [_BASE, _PARENT]:
        p = os.path.join(folder, filename)
        if os.path.exists(p):
            print(f"[ICON] {filename} found", flush=True)
            return p
    print(f"[ICON] {filename} not found, using fallback", flush=True)
    return ""


def _load_icon(path, fallback_color="#2D2926", fallback_letter="S"):
    if path and os.path.exists(path):
        return QIcon(path)
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(fallback_color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.setPen(QPen(QColor("#FFFFFF")))
    f = QFont("Georgia", 22, QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, fallback_letter)
    p.end()
    return QIcon(pm)


# ===============================================================
# STYLESHEET
# ===============================================================
STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {Theme.BG};
    color: {Theme.TEXT};
    font-family: 'Georgia', 'Palatino Linotype', 'Book Antiqua', serif;
}}
#Sidebar {{
    background-color: {Theme.SURFACE};
    border-right: 1px solid {Theme.BORDER};
    min-width: 220px;
    max-width: 220px;
}}
#NavButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    color: {Theme.ACCENT_SOFT};
}}
#NavButton:hover {{ background-color: {Theme.CARD}; color: {Theme.TEXT}; }}
#NavButton[active="true"] {{
    background-color: {Theme.HIGHLIGHT_LT};
    color: {Theme.ACCENT};
    font-weight: 600;
}}
#TopBar {{
    background-color: {Theme.SURFACE};
    border-bottom: 1px solid {Theme.BORDER};
    min-height: 60px;
    max-height: 60px;
}}
#SearchBar {{
    background-color: {Theme.CARD};
    border: 1.5px solid {Theme.BORDER};
    border-radius: {Theme.RADIUS_LG};
    padding: 12px 18px;
    font-size: 15px;
    color: {Theme.TEXT};
}}
#SearchBar:focus {{
    border: 1.5px solid {Theme.HIGHLIGHT};
    background-color: {Theme.SURFACE};
}}
#SearchBtn {{
    background-color: {Theme.ACCENT};
    color: white;
    border: none;
    border-radius: {Theme.RADIUS};
    padding: 12px 22px;
    font-size: 13px;
    font-weight: 600;
}}
#SearchBtn:hover   {{ background-color: {Theme.ACCENT_SOFT}; }}
#SearchBtn:pressed {{ background-color: {Theme.HIGHLIGHT}; }}
#Card {{
    background-color: {Theme.SURFACE};
    border: 1px solid {Theme.BORDER};
    border-radius: {Theme.RADIUS_LG};
}}
#ToggleHeroCard {{
    background-color: {Theme.ACCENT};
    border-radius: 16px;
    border: none;
}}
#WordChip {{
    background-color: {Theme.CARD};
    border: 1px solid {Theme.BORDER};
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    color: {Theme.ACCENT_SOFT};
}}
#WordChip:hover {{
    background-color: {Theme.HIGHLIGHT_LT};
    color: {Theme.ACCENT};
    border-color: {Theme.HIGHLIGHT};
}}
#SectionTitle {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
    color: {Theme.TEXT_MUTED};
}}
QComboBox {{
    background-color: {Theme.CARD};
    border: 1.5px solid {Theme.BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: {Theme.TEXT};
    min-width: 200px;
}}
QComboBox:hover {{ border-color: {Theme.HIGHLIGHT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {Theme.SURFACE};
    border: 1px solid {Theme.BORDER};
    selection-background-color: {Theme.HIGHLIGHT_LT};
    selection-color: {Theme.ACCENT};
    border-radius: 8px;
    padding: 4px;
}}
QCheckBox {{ font-size: 13px; color: {Theme.TEXT}; spacing: 10px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1.5px solid {Theme.BORDER};
    border-radius: 5px;
    background-color: {Theme.CARD};
}}
QCheckBox::indicator:checked {{
    background-color: {Theme.ACCENT};
    border-color: {Theme.ACCENT};
}}
QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {Theme.BORDER}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
#SecondaryBtn {{
    background-color: {Theme.CARD};
    color: {Theme.ACCENT};
    border: 1.5px solid {Theme.BORDER};
    border-radius: {Theme.RADIUS};
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 500;
}}
#SecondaryBtn:hover {{
    background-color: {Theme.HIGHLIGHT_LT};
    border-color: {Theme.HIGHLIGHT};
}}
#GoldBtn {{
    background-color: {Theme.HIGHLIGHT};
    color: {Theme.SURFACE};
    border: none;
    border-radius: {Theme.RADIUS};
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
}}
#GoldBtn:hover {{ background-color: #B8945A; }}
#Divider {{
    background-color: {Theme.BORDER};
    max-height: 1px; min-height: 1px;
}}
"""


# ===============================================================
# HELPERS
# ===============================================================
def lbl(text, size=13, weight=400, color=None, obj_name=None):
    w = QLabel(text)
    f = QFont()
    f.setFamilies(["Georgia", "Palatino Linotype", "Book Antiqua", "serif"])
    f.setPointSize(size)
    f.setWeight(
        QFont.Weight.Bold     if weight >= 700 else
        QFont.Weight.DemiBold if weight >= 600 else
        QFont.Weight.Medium   if weight >= 500 else
        QFont.Weight.Normal
    )
    w.setFont(f)
    if color:
        w.setStyleSheet(f"color: {color};")
    if obj_name:
        w.setObjectName(obj_name)
    return w


def divider():
    d = QFrame()
    d.setObjectName("Divider")
    d.setFrameShape(QFrame.Shape.HLine)
    return d


def shadow(widget, blur=20, ox=0, oy=4, color="#00000015"):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setOffset(ox, oy)
    eff.setColor(QColor(color))
    widget.setGraphicsEffect(eff)


# ===============================================================
# ANIMATED TOGGLE SWITCH
# ===============================================================
class ToggleSwitch(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 34)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._pos = 1.0
        self._connected = False
        self._timer = QTimer(self)
        self._timer.setInterval(12)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, e):
        super().showEvent(e)
        if STATE and not self._connected:
            self._pos = 1.0 if STATE.active else 0.0
            STATE.toggled.connect(lambda _: self._timer.start())
            self._connected = True
        self.update()

    def _tick(self):
        target = 1.0 if (STATE and STATE.active) else 0.0
        diff = target - self._pos
        if abs(diff) < 0.04:
            self._pos = target; self._timer.stop()
        else:
            self._pos += diff * 0.25
        self.update()

    def mousePressEvent(self, _):
        if STATE:
            STATE.toggle()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._pos
        off_c = QColor("#D0C8BE")
        on_c  = QColor("#27AE60")
        track = QColor(
            int(off_c.red()   + (on_c.red()   - off_c.red())   * t),
            int(off_c.green() + (on_c.green() - off_c.green()) * t),
            int(off_c.blue()  + (on_c.blue()  - off_c.blue())  * t),
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 0, 64, 34, 17, 17)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(int(4 + t * 30), 4, 26, 26)
        p.end()


# ===============================================================
# TOGGLE HERO CARD
# ===============================================================
class ToggleHeroCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToggleHeroCard")
        self.setMinimumHeight(160)
        self._build()
        shadow(self, blur=32, ox=0, oy=8, color="#00000025")

    def _build(self):
        self._state_connected = False
        outer = QHBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(0)

        left = QVBoxLayout(); left.setSpacing(6)

        sr = QHBoxLayout(); sr.setSpacing(8)
        sr.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._dot = QLabel("●")
        df = QFont(); df.setFamilies(["Georgia", "serif"]); df.setPointSize(10)
        self._dot.setFont(df)
        self._status_lbl = QLabel()
        sf = QFont(); sf.setFamilies(["Georgia", "serif"])
        sf.setPointSize(11); sf.setWeight(QFont.Weight.DemiBold)
        self._status_lbl.setFont(sf)
        sr.addWidget(self._dot); sr.addWidget(self._status_lbl)
        left.addLayout(sr)

        self._headline = QLabel()
        hf = QFont(); hf.setFamilies(["Georgia", "serif"])
        hf.setPointSize(20); hf.setWeight(QFont.Weight.Bold)
        self._headline.setFont(hf)
        left.addWidget(self._headline)

        self._desc = QLabel(); self._desc.setWordWrap(True)
        descf = QFont(); descf.setFamilies(["Georgia", "serif"]); descf.setPointSize(12)
        self._desc.setFont(descf)
        left.addWidget(self._desc)

        left.addSpacing(12)

        self._trigger = QLabel()
        tf = QFont(); tf.setFamilies(["Georgia", "serif"])
        tf.setPointSize(11); tf.setWeight(QFont.Weight.Medium)
        self._trigger.setFont(tf)
        left.addWidget(self._trigger)

        outer.addLayout(left, stretch=1)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(ToggleSwitch())
        outer.addLayout(right)

    def showEvent(self, e):
        super().showEvent(e)
        if STATE and not self._state_connected:
            self._refresh(STATE.active)
            STATE.toggled.connect(self._refresh)
            self._state_connected = True

    def _refresh(self, active):
        if active:
            self._dot.setStyleSheet("color: #4CD97B;")
            self._status_lbl.setStyleSheet("color: #4CD97B;")
            self._status_lbl.setText("Active")
            self._headline.setStyleSheet("color: #FFFFFF;")
            self._headline.setText("Saras is listening")
            self._desc.setStyleSheet("color: rgba(255,255,255,0.55);")
            self._desc.setText(
                "Double-click any word to instantly look it up.\n"
                "Saras works silently in the background."
            )
            self._trigger.setStyleSheet(
                "color:rgba(255,255,255,0.9);"
                "background-color:rgba(255,255,255,0.12);"
                "border-radius:10px;padding:4px 14px;"
            )
            self._trigger.setText("Trigger: Double-click")
        else:
            self._dot.setStyleSheet("color: #E57373;")
            self._status_lbl.setStyleSheet("color: #E57373;")
            self._status_lbl.setText("Paused")
            self._headline.setStyleSheet("color: rgba(255,255,255,0.55);")
            self._headline.setText("Saras is paused")
            self._desc.setStyleSheet("color: rgba(255,255,255,0.30);")
            self._desc.setText(
                "Toggle on to start looking up words by double-clicking\n"
                "any text - anywhere on your screen."
            )
            self._trigger.setStyleSheet(
                "color:rgba(255,255,255,0.35);"
                "background-color:rgba(255,255,255,0.06);"
                "border-radius:10px;padding:4px 14px;"
            )
            self._trigger.setText("Trigger: Double-click")


# ===============================================================
# NAV BUTTON
# ===============================================================
class NavButton(QPushButton):
    def __init__(self, icon_char, text, parent=None):
        super().__init__(f"  {icon_char}   {text}", parent)
        self.setObjectName("NavButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(42)

    def set_active(self, val):
        self.setProperty("active", "true" if val else "false")
        self.style().unpolish(self); self.style().polish(self)


# ===============================================================
# FLOW LAYOUT
# ===============================================================
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):       self._items.append(item)
    def setSpacing(self, s):       self._spacing = s
    def count(self):               return len(self._items)
    def itemAt(self, i):           return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i):           return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self):   return True
    def heightForWidth(self, w):   return self._do_layout(QRect(0, 0, w, 0), test=True)
    def setGeometry(self, r):      super().setGeometry(r); self._do_layout(r, test=False)
    def sizeHint(self):            return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for i in self._items: s = s.expandedTo(i.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test):
        m = self.contentsMargins()
        x, y, line_h = rect.x() + m.left(), rect.y() + m.top(), 0
        for item in self._items:
            w = item.sizeHint()
            nx = x + w.width() + self._spacing
            if nx - self._spacing > rect.right() and line_h > 0:
                x = rect.x() + m.left()
                y += line_h + self._spacing
                nx = x + w.width() + self._spacing
                line_h = 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), w))
            x = nx; line_h = max(line_h, w.height())
        return y + line_h - rect.y() + m.bottom()


# ===============================================================
# PAGE: HOME
# ===============================================================
class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32); root.setSpacing(24)

        root.addWidget(lbl("Good morning", 22, 700, Theme.TEXT))
        root.addWidget(lbl("What word are you looking up today?", 13, 400, Theme.TEXT_SUB))

        sc = QWidget(); sc.setObjectName("Card")
        sl = QHBoxLayout(sc); sl.setContentsMargins(4, 4, 4, 4); sl.setSpacing(8)
        search = QLineEdit(); search.setObjectName("SearchBar")
        search.setPlaceholderText("Search a word..."); search.setMinimumHeight(46)
        btn = QPushButton("Look up"); btn.setObjectName("SearchBtn")
        btn.setMinimumHeight(46); btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        sl.addWidget(search); sl.addWidget(btn)
        shadow(sc, blur=24, oy=6, color="#0000000A")
        root.addWidget(sc)

        sr = QHBoxLayout(); sr.setSpacing(16)
        for val, cap in [("47","Words Today"),("312","This Week"),("50","History Limit")]:
            card = QWidget(); card.setObjectName("Card")
            cl = QVBoxLayout(card); cl.setContentsMargins(20,16,20,16); cl.setSpacing(4)
            cl.addWidget(lbl(val,28,700,Theme.ACCENT)); cl.addWidget(lbl(cap,11,500,Theme.TEXT_MUTED))
            shadow(card,blur=16,oy=3,color="#0000000A"); sr.addWidget(card)
        root.addLayout(sr)

        root.addWidget(lbl("RECENT LOOKUPS", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        cc = QWidget(); fl = FlowLayout(cc); fl.setSpacing(8)
        for w in ["ephemeral","serendipity","eloquent","luminous","tenacious",
                  "paradox","resilience","ambiguous","clarity","benevolent",
                  "nostalgia","labyrinth","vivid","profound","intricate",
                  "wanderlust","euphoria","solace","cogent","melancholy"]:
            chip = QPushButton(w); chip.setObjectName("WordChip")
            chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); fl.addWidget(chip)
        scroll.setWidget(cc); scroll.setMinimumHeight(140)
        root.addWidget(scroll); root.addStretch()
        info = lbl("You looked up 47 words today  -  3 away from your daily record", 11, 400, Theme.TEXT_MUTED)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter); root.addWidget(info)


# ===============================================================
# PAGE: HISTORY
# ===============================================================
class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(32,32,32,32); root.setSpacing(20)
        hdr = QHBoxLayout()
        hdr.addWidget(lbl("History", 22, 700, Theme.TEXT)); hdr.addStretch()
        cb = QPushButton("Clear All"); cb.setObjectName("SecondaryBtn")
        cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); hdr.addWidget(cb)
        root.addLayout(hdr)
        root.addWidget(lbl("Your last 50 lookups are saved locally.", 13, 400, Theme.TEXT_SUB))
        root.addWidget(divider())

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        cl = QVBoxLayout(container); cl.setContentsMargins(0,0,0,0); cl.setSpacing(8)
        for word, pos, ts in [
            ("ephemeral","adj.","Today, 2:41 PM"), ("serendipity","noun","Today, 1:05 PM"),
            ("eloquent","adj.","Today, 11:32 AM"), ("tenacious","adj.","Today, 10:17 AM"),
            ("paradox","noun","Today, 9:48 AM"),   ("resilience","noun","Yesterday, 7:22 PM"),
            ("ambiguous","adj.","Yesterday, 3:55 PM"), ("clarity","noun","Yesterday, 2:10 PM"),
            ("nostalgia","noun","Mon, Feb 20"),
        ]:
            row = QWidget(); row.setObjectName("Card")
            row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            rl = QHBoxLayout(row); rl.setContentsMargins(16,12,16,12)
            lft = QVBoxLayout(); lft.setSpacing(2)
            lft.addWidget(lbl(word,14,600,Theme.TEXT)); lft.addWidget(lbl(pos,11,400,Theme.TEXT_MUTED))
            rl.addLayout(lft); rl.addStretch(); rl.addWidget(lbl(ts,11,400,Theme.TEXT_MUTED))
            cl.addWidget(row)
        cl.addStretch(); scroll.setWidget(container); root.addWidget(scroll)


# ===============================================================
# PAGE: SETTINGS
# ===============================================================
class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(32,32,32,32); root.setSpacing(0)

        root.addWidget(lbl("Settings", 22, 700, Theme.TEXT))
        root.addSpacing(4)
        root.addWidget(lbl("Customize how Saras works for you.", 13, 400, Theme.TEXT_SUB))
        root.addSpacing(24)

        root.addWidget(ToggleHeroCard())   # <-- the big synced toggle
        root.addSpacing(28)

        root.addWidget(lbl("ACTIVATION TRIGGER", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))
        root.addSpacing(8)
        root.addWidget(self._row(
            "Trigger Method", "How you activate Saras while reading a word.",
            self._combo(["Double-click","Ctrl + Double-click","Middle-click","Ctrl + Shift"])
        ))
        root.addSpacing(24)

        root.addWidget(lbl("SYSTEM", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))
        root.addSpacing(8)
        root.addWidget(self._row(
            "Start with Windows", "Launch Saras automatically when you log in.",
            QCheckBox("Enable startup")
        ))
        root.addSpacing(24)

        root.addWidget(lbl("APPEARANCE", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))
        root.addSpacing(8)
        root.addWidget(self._row(
            "Theme", "Choose between light and dark interface.",
            self._combo(["Light (Default)","Dark"])
        ))
        root.addSpacing(28)

        save = QPushButton("Save Preferences"); save.setObjectName("SearchBtn")
        save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save.setMaximumWidth(200); save.setMinimumHeight(42)
        root.addWidget(save); root.addStretch()

    def _combo(self, opts):
        cb = QComboBox()
        for o in opts: cb.addItem(o)
        cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return cb

    def _row(self, title, subtitle, control):
        row = QWidget(); row.setObjectName("Card")
        lay = QHBoxLayout(row); lay.setContentsMargins(20,16,20,16); lay.setSpacing(16)
        tc = QVBoxLayout(); tc.setSpacing(3)
        tc.addWidget(lbl(title,13,600,Theme.TEXT)); tc.addWidget(lbl(subtitle,11,400,Theme.TEXT_MUTED))
        lay.addLayout(tc,stretch=1); lay.addWidget(control)
        return row


# ===============================================================
# PAGE: SUPPORT
# ===============================================================
class SupportPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(32,32,32,32); root.setSpacing(20)
        root.addWidget(lbl("Support & Feedback", 22, 700, Theme.TEXT))
        root.addWidget(lbl("We're here to help. Reach out any time.", 13, 400, Theme.TEXT_SUB))
        root.addWidget(divider())
        for title, sub, btn_text, btn_id in [
            ("Email Support",     "udhyog@saras.app",                               "Send Email","GoldBtn"),
            ("Send Feedback",     "Share your thoughts to help us improve Saras.",   "Open Form", "SecondaryBtn"),
            ("Check for Updates", "Current version: 0.1  -  Checks GitHub Releases", "Check Now", "SecondaryBtn"),
        ]:
            card = QWidget(); card.setObjectName("Card")
            cl = QHBoxLayout(card); cl.setContentsMargins(20,18,20,18)
            lft = QVBoxLayout(); lft.setSpacing(4)
            lft.addWidget(lbl(title,13,600,Theme.TEXT))
            lft.addWidget(lbl(sub,11,400,Theme.HIGHLIGHT if "saras.app" in sub else Theme.TEXT_MUTED))
            cl.addLayout(lft); cl.addStretch()
            b = QPushButton(btn_text); b.setObjectName(btn_id)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); b.setMinimumHeight(38)
            cl.addWidget(b); root.addWidget(card)
        root.addStretch()
        footer = lbl("Saras v0.1  -  Made with care  -  2026 Saras", 11, 400, Theme.TEXT_MUTED)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter); root.addWidget(footer)


# ===============================================================
# PAGE: ABOUT
# ===============================================================
class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(32,32,32,32); root.setSpacing(20)
        root.addWidget(lbl("About Saras", 22, 700, Theme.TEXT))
        root.addWidget(lbl("Version 0.1  -  Early Access", 12, 400, Theme.TEXT_MUTED))
        root.addWidget(divider())

        blurb = QWidget(); blurb.setObjectName("Card")
        bl = QVBoxLayout(blurb); bl.setContentsMargins(24,20,24,20); bl.setSpacing(6)
        bl.addWidget(lbl("Saras.", 28, 700, Theme.ACCENT))
        d = lbl("Saras brings instant word definitions to your fingertips,\n"
                "wherever you're reading - quietly running in the background.", 13, 400, Theme.TEXT_SUB)
        d.setWordWrap(True); bl.addWidget(d)
        shadow(blurb, blur=16, oy=3, color="#0000000A"); root.addWidget(blurb)

        root.addWidget(lbl("SEND US A GREETING", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))
        mc = QWidget(); mc.setObjectName("Card")
        ml = QVBoxLayout(mc); ml.setContentsMargins(20,18,20,18); ml.setSpacing(12)
        prompt = lbl("Have a thought or kind word? We read every message.", 12, 400, Theme.TEXT_SUB)
        prompt.setWordWrap(True); ml.addWidget(prompt)

        self._msg = QTextEdit()
        self._msg.setPlaceholderText("Write your message here...")
        self._msg.setMinimumHeight(100); self._msg.setMaximumHeight(130)
        self._msg.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.CARD}; border: 1.5px solid {Theme.BORDER};
                border-radius: 10px; padding: 10px 14px;
                font-family: Georgia, serif; font-size: 13px; color: {Theme.TEXT};
            }}
            QTextEdit:focus {{ border: 1.5px solid {Theme.HIGHLIGHT}; background-color: {Theme.SURFACE}; }}
        """)
        ml.addWidget(self._msg)

        nr = QHBoxLayout(); nr.setSpacing(10)
        self._name = QLineEdit(); self._name.setObjectName("SearchBar")
        self._name.setPlaceholderText("Your name (optional)")
        self._name.setMinimumHeight(40); self._name.setMaximumWidth(220)
        nr.addWidget(self._name); nr.addStretch()
        self._send_btn = QPushButton("Send Greeting"); self._send_btn.setObjectName("GoldBtn")
        self._send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._send_btn.setMinimumHeight(40); self._send_btn.clicked.connect(self._send)
        nr.addWidget(self._send_btn); ml.addLayout(nr)
        self._confirm = lbl("", 11, 500, Theme.SUCCESS)
        self._confirm.setAlignment(Qt.AlignmentFlag.AlignRight); self._confirm.hide()
        ml.addWidget(self._confirm); root.addWidget(mc); root.addStretch()
        lbl("Built with care  -  2026 Saras", 11, 400, Theme.TEXT_MUTED)

    def _send(self):
        msg = self._msg.toPlainText().strip()
        if not msg:
            self._confirm.setText("Please write a message first.")
            self._confirm.setStyleSheet(f"color:{Theme.DANGER};"); self._confirm.show(); return
        name = self._name.text().strip()
        body = f"From: {name}\n\n{msg}" if name else msg
        webbrowser.open(
            f"mailto:udhyog@saras.app"
            f"?subject={urllib.parse.quote('A Greeting from a Saras User')}"
            f"&body={urllib.parse.quote(body)}"
        )
        self._confirm.setText("Opening your mail client... Thank you!")
        self._confirm.setStyleSheet(f"color:{Theme.SUCCESS};"); self._confirm.show()
        self._send_btn.setEnabled(False); self._send_btn.setText("Sent")
        QTimer.singleShot(5000, self._reset)

    def _reset(self):
        self._msg.clear(); self._name.clear(); self._confirm.hide()
        self._send_btn.setEnabled(True); self._send_btn.setText("Send Greeting")


# ===============================================================
# TRAY ICON  — synced with STATE, controls listener
# ===============================================================
class SarasTray(QSystemTrayIcon):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self._win = win
        self._icon_on  = _load_icon(_find_icon("lotus_running_green.ico"), "#27AE60", "ON")
        self._icon_off = _load_icon(_find_icon("lotus_sleeping_red.ico"),  "#C0392B", "OFF")

        self._sync_icon(STATE.active)
        STATE.toggled.connect(self._sync_icon)

        menu = QMenu()
        self._toggle_act = QAction()
        self._toggle_act.triggered.connect(STATE.toggle)
        self._update_label(STATE.active)
        STATE.toggled.connect(self._update_label)
        menu.addAction(self._toggle_act)

        menu.addSeparator()
        open_act = QAction("Open Saras")
        open_act.triggered.connect(self._show_win)
        menu.addAction(open_act)

        menu.addSeparator()
        quit_act = QAction("Quit Saras")
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activate)
        self.show()
        self.showMessage("Saras",
            "Running in background. Double-click any word to look it up.",
            QSystemTrayIcon.MessageIcon.Information, 3000)

    def _sync_icon(self, active):
        self.setIcon(self._icon_on if active else self._icon_off)
        self.setToolTip("Saras - Active" if active else "Saras - Paused")

    def _update_label(self, active):
        self._toggle_act.setText("Turn Off" if active else "Turn On")

    def _on_activate(self, reason):
        # Single left-click → show the window
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_win()
        # Double-click → toggle the listener directly
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            STATE.toggle()

    def _show_win(self):
        self._win.show(); self._win.raise_(); self._win.activateWindow()

    def _quit(self):
        controller.stop()
        QApplication.instance().quit()


# ===============================================================
# MAIN WINDOW
# ===============================================================
class SarasApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Saras - Dictionary")
        self.setMinimumSize(860, 600); self.resize(960, 660)
        self.setWindowIcon(_load_icon(_find_icon("lotus_coin_v2.ico"), Theme.ACCENT, "S"))
        self._build()

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        ml = QVBoxLayout(central); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        ml.addWidget(self._top_bar())
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        body.addWidget(self._sidebar())
        self.stack = QStackedWidget()
        for page in [HomePage(), HistoryPage(), SettingsPage(), SupportPage(), AboutPage()]:
            self.stack.addWidget(page)
        body.addWidget(self.stack); ml.addLayout(body)

    def _top_bar(self):
        bar = QWidget(); bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar); lay.setContentsMargins(24,0,24,0)
        logo = lbl("Saras.", 18, 700, Theme.ACCENT)
        ver = lbl("v0.1", 10, 500, Theme.TEXT_MUTED)
        ver.setStyleSheet(f"color:{Theme.TEXT_MUTED};background-color:{Theme.CARD};"
                          f"border-radius:9px;padding:2px 8px;font-size:11px;")
        lay.addWidget(logo); lay.addWidget(ver); lay.addStretch()

        self._status_badge = QLabel()
        f = QFont(); f.setFamilies(["Georgia","serif"]); f.setPointSize(11)
        self._status_badge.setFont(f)
        self._refresh_badge(STATE.active)
        STATE.toggled.connect(self._refresh_badge)
        lay.addWidget(self._status_badge)

        pill = lbl("47 words today", 11, 500, Theme.HIGHLIGHT)
        pill.setStyleSheet(f"color:{Theme.HIGHLIGHT};background-color:{Theme.HIGHLIGHT_LT};"
                           f"border-radius:10px;padding:4px 12px;")
        lay.addWidget(pill)
        return bar

    def _refresh_badge(self, active):
        if active:
            self._status_badge.setText("Active")
            self._status_badge.setStyleSheet(
                "color:#27AE60;background-color:#E8F8EF;border-radius:10px;padding:4px 12px;")
        else:
            self._status_badge.setText("Paused")
            self._status_badge.setStyleSheet(
                "color:#C0392B;background-color:#FDECEA;border-radius:10px;padding:4px 12px;")

    def _sidebar(self):
        sb = QWidget(); sb.setObjectName("Sidebar")
        lay = QVBoxLayout(sb); lay.setContentsMargins(12,20,12,20); lay.setSpacing(4)
        self._nav_btns = []
        for icon, text, idx in [
            ("H","Home",0),("R","History",1),("S","Settings",2),("@","Support",3),("i","About",4)
        ]:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda _, i=idx: self._nav(i))
            self._nav_btns.append(btn); lay.addWidget(btn)
        self._nav_btns[0].set_active(True); lay.addStretch()
        v = lbl("Saras v0.1", 10, 400, Theme.TEXT_MUTED)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(v)
        return sb

    def _nav(self, index):
        for i, btn in enumerate(self._nav_btns): btn.set_active(i == index)
        self.stack.setCurrentIndex(index)

    def closeEvent(self, event):
        event.ignore(); self.hide()


# ===============================================================
# ENTRY POINT
# ===============================================================
def main():
    global STATE, controller

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    # STATE must be created after QApplication
    STATE = AppState()
    print("[SARAS] STATE ready, active =", STATE.active, flush=True)

    app.setStyleSheet(STYLESHEET)

    # Listener — start it, then wire STATE.toggled to start/stop it
    controller = ListenerController()
    controller.start()
    STATE.toggled.connect(lambda active: controller.start() if active else controller.stop())
    print("[SARAS] Listener wired to STATE", flush=True)

    # Queue processor — polls every 100ms for words to show popups
    queue_timer = QTimer()
    queue_timer.timeout.connect(process_queue)
    queue_timer.start(100)

    # Signal handling (Ctrl+C in terminal)
    def shutdown(*_):
        controller.stop()
        queue_timer.stop()
        app.quit()
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    sig_timer = QTimer(); sig_timer.timeout.connect(lambda: None); sig_timer.start(200)

    print("[SARAS] Building window...", flush=True)
    win = SarasApp()
    win.show()

    tray = SarasTray(win)
    print("[SARAS] All ready - entering event loop", flush=True)

    sys.exit(app.exec())


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        input("Press Enter to close...")