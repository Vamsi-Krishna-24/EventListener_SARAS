"""
saras_app.py  |  SARAS Backend  |  v0.3
═══════════════════════════════════════════════════════════════
  Runs three things in parallel:
    1. FastAPI server  (localhost:5000)  — talks to Electron UI
    2. ListenerController               — watches for trigger input
    3. SarasTray                        — system tray icon (green/red)

  PyQt6 is kept ONLY for the tray icon.
  All UI (including popups) is handled by Electron.

  Endpoints (FastAPI on :5000):
    GET  /status          → { listening, trigger_mode }
    POST /toggle          → { listening, trigger_mode } → saves + applies
    GET  /define?word=x   → DB lookup → fallback to REST API

  Popup trigger (Electron HTTP server on :5001):
    POST /show-popup      → { word, definition, examples, synonyms }
═══════════════════════════════════════════════════════════════
"""

import sys
import os
import time
import signal
import threading
import queue

print("[SARAS] Starting...", flush=True)

# ───────────────────────────────────────────────
# WIN32: DPI-safe cursor position
# ───────────────────────────────────────────────
# IMPORTANT — Do NOT set DPI-awareness anywhere in this process.
#   • Remove SetProcessDpiAwareness / SetProcessDPIAware calls from listener1.py
#   • Remove dpi_aware.manifest from Saras.spec
# Keeping the process DPI-unaware means GetCursorPos returns virtualised
# logical coordinates — exactly the same space Electron uses for
# BrowserWindow positioning.  No conversion needed on either side.
import ctypes
import ctypes.wintypes as wintypes

def get_cursor_pos() -> tuple[int, int]:
    """Return current cursor position in logical (DPI-virtualised) pixels.
    Only valid when the process is DPI-unaware (Windows default)."""
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

import pyperclip
import uvicorn
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pynput import mouse, keyboard

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, pyqtSlot, QMetaObject, Qt as QtCore
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QPen, QAction

from db_handler import (
    get_word_meaning,
    init_profile_db,
    save_user_profile,
    get_user_profile,
    is_activated,
)
from listener1 import ListenerController

print("[SARAS] Imports OK", flush=True)


# ───────────────────────────────────────────────
# PATHS
# ───────────────────────────────────────────────
_BASE   = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_BASE)


def _find_icon(filename):
    for folder in [_BASE, _PARENT]:
        p = os.path.join(folder, filename)
        if os.path.exists(p):
            return p
    return ""


def _load_icon(filepath: str, fallback_color: str, label: str) -> QIcon:
    """
    Load a tray icon from an .ico file.
    If the file is missing, generate a small coloured circle with a label
    so the tray icon is never blank.
    """
    if filepath and os.path.exists(filepath):
        return QIcon(filepath)

    # Fallback — draw a 64×64 coloured circle with the label text
    pix = QPixmap(64, 64)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(fallback_color))
    painter.setPen(QPen(QColor(fallback_color), 0))
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    return QIcon(pix)


# ───────────────────────────────────────────────
# SHARED STATE  — single source of truth
# ───────────────────────────────────────────────
class AppState(QObject):
    """
    Owns two values: active (bool) and trigger_mode (str).
    Any change emits toggled(bool) so tray icon stays in sync.
    FastAPI reads/writes this from a background thread via
    thread-safe set_active() and set_trigger_mode().
    """
    toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._active       = True
        self._trigger_mode = "double_click"   # or "long_press"
        self._lock         = threading.Lock()

    # ── active ──────────────────────────────────
    @property
    def active(self):
        return self._active

    def set_active(self, val: bool):
        with self._lock:
            if val == self._active:
                return
            self._active = val
        # Thread-safe emit — works whether called from FastAPI thread or Qt main thread
        QMetaObject.invokeMethod(
            self, "_emit_toggled",
            QtCore.ConnectionType.QueuedConnection
        )

    @pyqtSlot()
    def _emit_toggled(self):
        """Always runs on Qt main thread due to QueuedConnection."""
        self.toggled.emit(self._active)

    def toggle(self):
        self.set_active(not self._active)

    # ── trigger_mode ────────────────────────────
    @property
    def trigger_mode(self):
        return self._trigger_mode

    def set_trigger_mode(self, mode: str):
        if mode not in ("double_click", "long_press"):
            return
        with self._lock:
            self._trigger_mode = mode
        # update the live listener immediately — no restart needed
        if controller:
            controller.set_trigger_mode(mode)


STATE      = None   # assigned after QApplication
controller = None   # ListenerController — assigned in main()
tray       = None   # SarasTray — assigned in main() or after activation
_tray_needed = threading.Event()  # set by /start-listener to trigger tray creation on Qt thread


# ───────────────────────────────────────────────
# WORD QUEUE + POPUP PROCESSOR
# ───────────────────────────────────────────────
word_queue = queue.Queue()

ELECTRON_POPUP_URL = "http://127.0.0.1:5001/show-popup"


def _post_to_electron(payload: dict):
    """
    Fire-and-forget POST to Electron's popup server.
    Runs in a daemon thread so it never blocks the Qt main thread.
    Silently ignores connection errors (Electron may not be ready yet).
    """
    try:
        with httpx.Client(timeout=3) as client:
            r = client.post(ELECTRON_POPUP_URL, json=payload)
            if r.status_code != 200:
                print(f"[POPUP] Electron returned {r.status_code}", flush=True)
    except Exception as e:
        print(f"[POPUP] Could not reach Electron popup server: {e}", flush=True)


# ── Dedup guard ─────────────────────────────────────────────────────────────
_last_popup_word: str  = ""
_last_popup_time: float = 0.0
POPUP_COOLDOWN_S: float = 10.0


WIKI_HEADERS = {
    "User-Agent": "SARAS-App/1.0 (https://github.com/saras; saras@example.com) python-httpx",
    "Accept":     "application/json",
}


def _fetch_wiki(word: str) -> tuple[str, str]:
    """
    Search Wikipedia for `word` and return (summary, page_url).
    Uses opensearch first to avoid disambiguation pages, then fetches
    the full summary for the best matching article title.
    Returns ("", "") if nothing useful is found.
    """
    try:
        # Step 1 — opensearch: find the best article title for this word
        search_r = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": word, "limit": 3, "format": "json"},
            headers=WIKI_HEADERS,
            timeout=5,
        )
        best_title = None
        if search_r.status_code == 200:
            results = search_r.json()
            titles  = results[1] if len(results) > 1 else []
            for title in titles:
                if "(disambiguation)" not in title.lower():
                    best_title = title
                    break

        if not best_title:
            return ("", "")

        # Step 2 — fetch the summary for that specific article
        sum_r = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{best_title.replace(' ', '_')}",
            timeout=5,
            headers=WIKI_HEADERS,
        )
        if sum_r.status_code == 200:
            wdata   = sum_r.json()
            extract = wdata.get("extract", "")
            if extract and wdata.get("type") != "disambiguation":
                sentences = extract.split(". ")
                summary   = ". ".join(sentences[:2]).strip()
                if not summary.endswith("."):
                    summary += "."
                url = wdata.get("content_urls", {}).get("desktop", {}).get("page", "")
                return (summary, url)

    except Exception as e:
        print(f"[WIKI] fetch failed for '{word}': {e}", flush=True)

    return ("", "")


ELECTRON_WIKI_URL = "http://127.0.0.1:5001/update-wiki"


def _post_wiki_update(word: str, wiki_summary: str, wiki_url: str):
    """POST just the Wikipedia data to the already-open popup."""
    try:
        with httpx.Client(timeout=3) as client:
            r = client.post(ELECTRON_WIKI_URL, json={
                "word":        word,
                "wikiSummary": wiki_summary,
                "wikiUrl":     wiki_url,
            })
            print(f"[WIKI] update sent for '{word}' → {r.status_code}", flush=True)
    except Exception as e:
        print(f"[WIKI] update post failed for '{word}': {e}", flush=True)


def _build_and_post(word: str, result: dict | None, click_x: int, click_y: int):
    """
    Called in a background thread.
    Step 1 — POST dict data immediately so popup appears instantly.
    Step 2 — Fetch Wikipedia, then POST /update-wiki to fill the wiki tab.
    """
    definition = ""
    examples: list = []
    synonyms: list = []

    if result:
        # ── Local DB hit ─────────────────────────
        definition = result.get("definition", "")
        examples   = result.get("examples",   [])
        synonyms   = result.get("synonyms",   [])
    else:
        # ── DB miss → try dictionaryapi.dev ──────
        try:
            r = httpx.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()[0]
                for m in data.get("meanings", []):
                    for d in m.get("definitions", []):
                        if not definition:
                            definition = d.get("definition", "")
                        if d.get("example"):
                            examples.append(d["example"])
                    synonyms.extend(m.get("synonyms", []))
                examples = examples[:3]
                synonyms = synonyms[:5]
        except Exception as e:
            print(f"[DICT] dictionaryapi.dev failed for '{word}': {e}", flush=True)

    display_word = result.get("word", word) if result else word

    # ── Step 1: send dict data immediately — popup opens right away ──────
    _post_to_electron({
        "word":        display_word,
        "definition":  definition or "No definition found.",
        "examples":    examples,
        "synonyms":    synonyms,
        "wikiSummary": "",
        "wikiUrl":     "",
        "clickX":      click_x,
        "clickY":      click_y,
    })
    print(f"[DICT] popup opened for '{display_word}'", flush=True)
    print(f"[COORD DEBUG] word='{display_word}' clickX={click_x} clickY={click_y}", flush=True)

    # ── Step 2: fetch Wikipedia and push update to the open popup ────────
    print(f"[WIKI] fetching for '{word}'...", flush=True)
    wiki_summary, wiki_url = _fetch_wiki(word)
    print(f"[WIKI] result for '{word}': summary={wiki_summary[:60] if wiki_summary else 'EMPTY'}", flush=True)
    if wiki_summary:
        _post_wiki_update(display_word, wiki_summary, wiki_url)


def process_queue():
    """Called every 100 ms by QTimer on the Qt main thread."""
    global _last_popup_word, _last_popup_time

    # Drain the whole queue, act only on the latest item
    items = []
    while not word_queue.empty():
        try:
            items.append(word_queue.get_nowait())
        except queue.Empty:
            break

    if not items:
        return

    # Each item is (word, x, y) — pynput captures these synchronously
    # at click time.  With the process kept DPI-unaware, these are
    # already logical/DIP coordinates that match Electron's space.
    word, click_x, click_y = items[-1]
    word = word.strip().lower()

    # Cooldown: skip if the same word fired recently
    now = time.monotonic()
    if word == _last_popup_word and (now - _last_popup_time) < POPUP_COOLDOWN_S:
        return
    _last_popup_word = word
    _last_popup_time = now

    result = get_word_meaning(word)

    # All network calls in a background thread — never block Qt
    threading.Thread(
        target=_build_and_post,
        args=(word, result, click_x, click_y),
        daemon=True,
    ).start()


# ───────────────────────────────────────────────
# TRAY ICON  — green = listening, red = paused
# ───────────────────────────────────────────────
class SarasTray(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._icon_on  = _load_icon(_find_icon("lotus_running_green.ico"), "#27AE60", "ON")
        self._icon_off = _load_icon(_find_icon("lotus_sleeping_red.ico"),  "#C0392B", "OFF")

        # build menu FIRST — _apply() references _toggle_act
        menu = QMenu()
        self._toggle_act = QAction()
        self._toggle_act.triggered.connect(STATE.toggle)
        menu.addAction(self._toggle_act)

        menu.addSeparator()
        quit_act = QAction("Quit SARAS")
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activate)

        # now safe to call _apply — _toggle_act exists
        self._last_known = None
        self._apply(STATE.active)

        # signal-based sync
        STATE.toggled.connect(self._apply)

        # poll every 500ms as safety net for cross-thread updates
        self._poll = QTimer()
        self._poll.timeout.connect(self._poll_state)
        self._poll.start(500)

        self.show()

        self.showMessage(
            "SARAS",
            "Running in the background. Double-click any word to look it up.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def _poll_state(self):
        """Catches any state changes that the signal missed (cross-thread safety)."""
        if STATE.active != self._last_known:
            self._apply(STATE.active)

    def _apply(self, active):
        self._last_known = active
        self.setIcon(self._icon_on if active else self._icon_off)
        self.setToolTip("SARAS — Active" if active else "SARAS — Paused")
        self._toggle_act.setText("Turn Off" if active else "Turn On")

    def _on_activate(self, reason):
        # double-click tray icon → toggle
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            STATE.toggle()

    def _quit(self):
        if controller:
            controller.stop()
        # Tell Electron to shut down cleanly — it will also kill this process
        try:
            import httpx
            with httpx.Client(timeout=2) as c:
                c.post("http://127.0.0.1:5001/quit")
        except Exception:
            pass  # if Electron is already gone, just quit directly
        QApplication.instance().quit()


# ───────────────────────────────────────────────
# FASTAPI APP
# ───────────────────────────────────────────────
api = FastAPI(title="SARAS API")

# Allow Electron (file:// or localhost) to call the API
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToggleRequest(BaseModel):
    listening:    bool
    trigger_mode: str   # "double_click" or "long_press"


@api.get("/status")
def get_status():
    """Electron polls this every 2 s to keep UI in sync with tray."""
    return {
        "listening":    STATE.active,
        "trigger_mode": STATE.trigger_mode,
    }


@api.post("/toggle")
def post_toggle(body: ToggleRequest):
    """
    Electron calls this when user changes toggle or trigger mode.
    STATE change automatically syncs the tray icon via Qt signal.
    """
    STATE.set_active(body.listening)
    STATE.set_trigger_mode(body.trigger_mode)

    # start/stop listener based on new state
    if body.listening:
        if controller and not controller.is_running():
            controller.start()
    else:
        if controller and controller.is_running():
            controller.stop()

    return {
        "listening":    STATE.active,
        "trigger_mode": STATE.trigger_mode,
    }


@api.get("/define")
async def define_word(word: str):
    """
    1. Query local DB first.
    2. If not found, fall back to dictionaryapi.dev.
    """
    if not word or not word.strip():
        return {"error": "empty word"}

    word = word.strip().lower()

    # ── 1. Local DB ─────────────────────────────
    result = get_word_meaning(word)
    if result:
        return {
            "source":     "db",
            "word":       result["word"],
            "definition": result["definition"],
            "examples":   result["examples"],
            "synonyms":   result["synonyms"],
        }

    # ── 2. Fallback: public REST API ─────────────
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            )
        if r.status_code == 200:
            data = r.json()[0]
            meanings  = data.get("meanings", [])
            phonetics = data.get("phonetics", [])

            definition = ""
            examples   = []
            synonyms   = []

            for m in meanings:
                for d in m.get("definitions", []):
                    if not definition:
                        definition = d.get("definition", "")
                    if d.get("example"):
                        examples.append(d["example"])
                synonyms.extend(m.get("synonyms", []))

            phonetic = next(
                (p["text"] for p in phonetics if p.get("text")), ""
            )

            return {
                "source":     "api",
                "word":       data.get("word", word),
                "phonetic":   phonetic,
                "definition": definition,
                "examples":   examples[:3],
                "synonyms":   synonyms[:5],
            }
    except Exception as e:
        print(f"[API] Fallback failed: {e}", flush=True)

    return {"error": "not found", "word": word}


@api.get("/check-activation")
def check_activation():
    """
    Called by main.js on every app launch.
    Returns activation status and user profile if found locally.
    """
    profile = get_user_profile()
    if profile:
        return {
            "activated":  True,
            "first_name": profile["first_name"],
            "last_name":  profile["last_name"],
            "email":      profile["email"],
        }
    return { "activated": False }


class ActivateRequest(BaseModel):
    license_key: str


@api.post("/activate")
async def activate_license(body: ActivateRequest):
    """
    Called by onboarding.html when user submits their license key.
    1. Forwards the key to getsaras.com/payments/activate/
    2. On success, saves the profile locally and returns it to Electron.
    """
    if not body.license_key or not body.license_key.strip():
        return { "error": "License key is required" }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://getsaras.com/payments/activate/",
                json={ "license_key": body.license_key.strip() }
            )

        if r.status_code == 200:
            data = r.json()

            if data.get("status") == "activated":
                save_user_profile(
                    first_name=  data["first_name"],
                    last_name=   data["last_name"],
                    email=       data["email"],
                    license_key= body.license_key.strip(),
                )
                return {
                    "success":    True,
                    "first_name": data["first_name"],
                    "last_name":  data["last_name"],
                    "email":      data["email"],
                }

            # Server responded but key was rejected
            return { "success": False, "error": data.get("message", "Invalid license key") }

        # Non-200 from server
        return { "success": False, "error": f"Server returned {r.status_code}" }

    except httpx.TimeoutException:
        return { "success": False, "error": "Request timed out — check your internet connection" }
    except Exception as e:
        print(f"[ACTIVATE] Unexpected error: {e}", flush=True)
        return { "success": False, "error": "Something went wrong — please try again" }


@api.post("/start-listener")
def start_listener():
    """
    Called by main.js after first-time activation via navigate-to-main.
    Single entry point — starts listener and flags Qt thread to show tray.
    """
    if controller and not controller.is_running():
        controller.start()
        print("[SARAS] Listener started via /start-listener", flush=True)
    else:
        print("[SARAS] /start-listener: listener already running", flush=True)

    _tray_needed.set()
    return { "ok": True }


def _run_api():
    """Run FastAPI in a daemon thread — dies when main thread exits."""
    uvicorn.run(api, host="127.0.0.1", port=5000, log_level="warning")


# ───────────────────────────────────────────────
# ENTRY POINT
# ───────────────────────────────────────────────
def main():
    global STATE, controller

    # Qt needs this even though we have no main window
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Ensure profile DB + table exist before anything else runs
    init_profile_db()

    STATE = AppState()
    print(f"[SARAS] STATE ready — active={STATE.active}, trigger={STATE.trigger_mode}", flush=True)

    # ── Listener — only start if user is already activated ──────
    controller = ListenerController(
        word_queue=word_queue,
        trigger_mode=STATE.trigger_mode
    )
    if is_activated():
        controller.start()
        print("[SARAS] User activated — listener started", flush=True)
    else:
        print("[SARAS] Not activated — listener held until activation", flush=True)

    # Wire STATE.toggled → start/stop listener
    STATE.toggled.connect(
        lambda active: controller.start() if active else controller.stop()
    )
    print("[SARAS] Listener wired to STATE", flush=True)

    # ── Queue processor (popup timer) ───────────
    queue_timer = QTimer()
    queue_timer.timeout.connect(process_queue)
    queue_timer.start(100)

    # ── Tray check timer — creates tray on Qt thread after activation ──
    def _check_tray_needed():
        global tray
        if tray is None and _tray_needed.is_set():
            tray = SarasTray()
            _tray_needed.clear()
            print("[SARAS] Tray icon created after activation", flush=True)

    tray_check_timer = QTimer()
    tray_check_timer.timeout.connect(_check_tray_needed)
    tray_check_timer.start(300)

    # ── Tray — only show if user is already activated ────
    tray = SarasTray() if is_activated() else None
    if not tray:
        print("[SARAS] Not activated — tray icon held until activation", flush=True)

    # ── FastAPI in background thread ─────────────
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()
    print("[SARAS] FastAPI running on http://127.0.0.1:5000", flush=True)

    # ── Ctrl+C in terminal ───────────────────────
    def shutdown(*_):
        controller.stop()
        queue_timer.stop()
        app.quit()

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    # Qt needs a Python-side timer to actually process signals
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(200)

    print("[SARAS] All ready — entering event loop", flush=True)
    sys.exit(app.exec())


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        input("Press Enter to close...")