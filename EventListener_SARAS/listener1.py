# listener1.py  |  SARAS event listener  |  v0.4
# ═══════════════════════════════════════════════════════════════════════════
#
# Word-capture strategy (tried in this order every time):
#
#   1. Windows UI Automation (UIA)
#      Reads the focused element's text selection directly from the OS
#      accessibility layer — the same API used by Windows Narrator.
#      ✓ Zero clipboard contact.
#      ✓ Fixes the sentence-copy collision bug entirely.
#      ✗ A small number of apps (some games, legacy custom UIs) do not
#        expose UIA's TextPattern — falls through to option 2 in those cases.
#
#   2. Save → Ctrl+C → read → restore  (clipboard fallback)
#      Used only when UIA returns nothing.
#      The user's clipboard content is saved before and restored after,
#      so the disruption window is ~150 ms and the user never permanently
#      loses what they had copied.
#
# NOTE: Do NOT set DPI-awareness anywhere in this process.
#   Keeping Python DPI-unaware means pynput / GetCursorPos return
#   virtualised logical coordinates — the same space Electron uses for
#   BrowserWindow positioning on scaled displays (125 %, 150 %, etc.).
#
# ═══════════════════════════════════════════════════════════════════════════

import re
import time
import threading
import queue

import pyperclip
from pynput import mouse, keyboard


# ── UI Automation bootstrap ──────────────────────────────────────────────────
#
# We attempt to load Windows UIAutomationCore once at import time.
# If anything fails, _UIA_AVAILABLE stays False and every capture
# automatically falls through to the clipboard fallback — no extra
# code needed anywhere else.
#
# PyInstaller note:
#   comtypes writes generated bindings into comtypes/gen/ at runtime.
#   In a packaged build that directory may be read-only.  Fix: run
#   `python -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"`
#   once during your build step so the generated file is bundled.
#   Then the `import comtypes.gen.UIAutomationClient` line below
#   succeeds without needing GetModule() at runtime.
#
# ─────────────────────────────────────────────────────────────────────────────

_UIA_AVAILABLE       = False
_UIA_CLIENT_MODULE   = None          # comtypes.gen.UIAutomationClient, once loaded
_UIA_TEXT_PATTERN_ID = 10014         # Windows constant: UIA_TextPatternId

try:
    import comtypes          # noqa: F401 — needed for CoInitialize later
    import comtypes.client

    try:
        import comtypes.gen.UIAutomationClient as _UIA_CLIENT_MODULE
    except (ImportError, OSError):
        # First run on this machine / dev environment — generate the bindings.
        comtypes.client.GetModule("UIAutomationCore.dll")
        import comtypes.gen.UIAutomationClient as _UIA_CLIENT_MODULE

    _UIA_AVAILABLE = True
    print("[SARAS] UI Automation ready — clipboard will not be touched", flush=True)

except Exception as _uia_boot_err:
    print(
        f"[SARAS] UI Automation unavailable, clipboard fallback active: {_uia_boot_err}",
        flush=True,
    )


# ── Module-level helpers ─────────────────────────────────────────────────────

def _get_selected_text_uia() -> str:
    """
    Ask Windows UI Automation for the text currently selected in the
    focused element.  Returns the raw selected string, or "" if:
      • UIA is not available on this machine
      • the focused app does not implement IUIAutomationTextPattern
      • nothing is selected

    COM must be initialised per-thread; this function handles that.
    Safe to call from any daemon thread.
    """
    if not _UIA_AVAILABLE or _UIA_CLIENT_MODULE is None:
        return ""

    try:
        import comtypes
        import comtypes.client

        # Each OS thread needs its own COM apartment initialisation.
        # comtypes raises OSError(S_FALSE) — not a real error — when the
        # thread is already initialised; we swallow that silently.
        try:
            comtypes.CoInitialize()
        except OSError:
            pass

        # Build a fresh IUIAutomation proxy on this thread's apartment.
        automation = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=_UIA_CLIENT_MODULE.IUIAutomation,
        )

        focused = automation.GetFocusedElement()
        if focused is None:
            return ""

        raw_pattern = focused.GetCurrentPattern(_UIA_TEXT_PATTERN_ID)
        if raw_pattern is None:
            return ""

        text_pattern = raw_pattern.QueryInterface(
            _UIA_CLIENT_MODULE.IUIAutomationTextPattern
        )
        selections = text_pattern.GetSelection()

        if selections is None or selections.Length == 0:
            return ""

        return (selections.GetElement(0).GetText(-1) or "").strip()

    except Exception as exc:
        print(f"[UIA] Read error (will try fallback): {exc}", flush=True)
        return ""


def _get_selected_text_clipboard_fallback(simulate_ctrl_c_fn) -> str:
    """
    Clipboard save → Ctrl+C → read → restore.

    Called only when UIA returns nothing.  The user's clipboard content
    is always restored before this function returns — the window where
    the clipboard is temporarily different is ~150 ms.

    `simulate_ctrl_c_fn` is a callable (no args) that sends Ctrl+C
    to the currently focused application.
    """
    # ── 1. Save whatever the user already has on the clipboard ──────────────
    try:
        saved = pyperclip.paste()
    except Exception:
        saved = ""

    # ── 2. Plant a sentinel so we can detect Ctrl+C having no effect ────────
    #    (empty string is ambiguous — the user might genuinely have nothing)
    _SENTINEL = "\x00SARAS\x00"
    try:
        pyperclip.copy(_SENTINEL)
    except Exception:
        pass

    # ── 3. Ask the app to copy its current selection ─────────────────────────
    simulate_ctrl_c_fn()
    time.sleep(0.15)      # 150 ms — safe budget for even slow/remote apps

    # ── 4. Read the result ───────────────────────────────────────────────────
    try:
        result = pyperclip.paste().strip()
    except Exception:
        result = ""

    # If the sentinel is still there, the app did not respond to Ctrl+C
    if result == _SENTINEL.strip() or result == _SENTINEL:
        result = ""

    # ── 5. Restore the user's original clipboard content ─────────────────────
    try:
        pyperclip.copy(saved)
    except Exception:
        pass

    return result


def _is_single_word(text: str) -> bool:
    """
    Return True only when `text` looks like a single dictionary word.

    Accepts:
      • plain words           →  "ephemeral"
      • hyphenated compounds  →  "self-aware"
      • apostrophe contractions → "don't", "o'clock"
      • accented / Unicode letters → "naïve", "résumé"
      • max 50 characters

    Rejects:
      • anything with whitespace (multi-word selections, sentences)
      • URLs, email addresses, file paths (contain ://, @, \\, /)
      • purely numeric strings (digits only)
      • empty strings
    """
    if not text:
        return False

    # Strip surrounding punctuation that editors often attach to selections
    cleaned = text.strip("\"'""''()[]{}.,;:!?\n\r\t ")
    if not cleaned:
        return False

    # Hard length cap — no real dictionary word exceeds 50 chars
    if len(cleaned) > 50:
        return False

    # Must be a single token (no whitespace inside)
    if re.search(r"\s", cleaned):
        return False

    # Must not be a URL / path / email fragment
    if any(ch in cleaned for ch in ("://", "@", "\\", "/")):
        return False

    # Must contain at least one Unicode letter (rules out pure numbers, symbols)
    if not any(c.isalpha() for c in cleaned):
        return False

    # Final shape check: letters, digits, hyphens, apostrophes only
    if not re.fullmatch(r"[\w'\-]{1,50}", cleaned, re.UNICODE):
        return False

    return True


# ════════════════════════════════════════════════════════════════════════════
# ListenerController
# ════════════════════════════════════════════════════════════════════════════

class ListenerController:

    DOUBLE_CLICK_THRESHOLD = 0.30   # seconds between two clicks to count as double
    LONG_PRESS_THRESHOLD   = 0.55   # seconds held down to count as long press

    def __init__(self, word_queue: queue.Queue, trigger_mode: str = "double_click"):
        self.word_queue   = word_queue
        self.trigger_mode = trigger_mode

        self._kbd   = keyboard.Controller()
        self._mouse = mouse.Controller()

        self._listener = None

        self._last_click_time = None
        self._press_time      = None
        self._press_xy        = None

        self._stop_flag = threading.Event()
        self._lock      = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        if self._listener and self._listener.running:
            return
        self._stop_flag.clear()
        print(f"[INFO] Listener started ({self.trigger_mode})", flush=True)
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.start()

    def stop(self):
        print("[INFO] Listener stopped", flush=True)
        self._stop_flag.set()
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_trigger_mode(self, mode: str):
        """Switch trigger mode live — no listener restart needed."""
        if mode not in ("double_click", "long_press"):
            print(f"[WARN] Unknown trigger mode: {mode}", flush=True)
            return
        self.trigger_mode     = mode
        self._last_click_time = None
        self._press_time      = None
        print(f"[INFO] Trigger mode → {mode}", flush=True)

    def is_running(self) -> bool:
        return self._listener is not None and self._listener.running

    # ── Main click handler ────────────────────────────────────────────────────

    def _on_click(self, x, y, button, pressed):
        # x, y: logical pixel coordinates from pynput, captured synchronously
        # at click time.  DPI-unaware process = same space as Electron.
        if button != mouse.Button.left:
            return
        if self._stop_flag.is_set():
            return
        if self.trigger_mode == "double_click":
            self._handle_double_click(pressed, x, y)
        elif self.trigger_mode == "long_press":
            self._handle_long_press(pressed, x, y)

    # ── Double-click path ─────────────────────────────────────────────────────

    def _handle_double_click(self, pressed, x, y):
        if pressed:
            return   # act on the release of the second click, not the press

        now = time.time()
        with self._lock:
            last = self._last_click_time
            self._last_click_time = now

        if last and (now - last) < self.DOUBLE_CLICK_THRESHOLD:
            # Spin off immediately — the listener thread must never block
            threading.Thread(
                target=self._capture_word,
                args=(x, y),
                daemon=True,
            ).start()

    # ── Long-press path ───────────────────────────────────────────────────────

    def _handle_long_press(self, pressed, x, y):
        if pressed:
            self._press_time = time.time()
            self._press_xy   = (x, y)
        else:
            if not self._press_time:
                return

            duration         = time.time() - self._press_time
            click_x, click_y = self._press_xy or (x, y)
            self._press_time = None
            self._press_xy   = None

            if duration >= self.LONG_PRESS_THRESHOLD:
                print(f"[LOG] Long press detected ({duration:.2f}s)", flush=True)
                threading.Thread(
                    target=self._long_press_capture,
                    args=(click_x, click_y),
                    daemon=True,
                ).start()

    def _long_press_capture(self, x, y):
        """
        Stop the listener (its low-level hook swallows synthetic events),
        simulate a double-click at the original press position to select
        the word, capture it, then restart the listener.
        """
        # Stop the listener — its WH_MOUSE_LL hook intercepts synthetic
        # mouse events before they reach the target application, which
        # prevents the simulated double-click from selecting the word.
        if self._listener:
            self._listener.stop()
            self._listener = None

        try:
            # Let the OS fully process the user's button release
            time.sleep(0.05)

            # Return cursor to the exact press position (may have drifted
            # slightly during the hold)
            self._mouse.position = (x, y)
            time.sleep(0.02)

            # Simulate double-click to select the word under the cursor
            self._mouse.click(mouse.Button.left, 2)

            # Generous delay so the OS finishes updating the text selection
            time.sleep(0.15)

            self._capture_word(x, y)
        finally:
            # Restart the listener
            self._stop_flag.clear()
            self._listener = mouse.Listener(on_click=self._on_click)
            self._listener.start()

    # ── Core capture ──────────────────────────────────────────────────────────

    def _simulate_ctrl_c(self):
        """Send Ctrl+C to the currently focused window."""
        self._kbd.press(keyboard.Key.ctrl)
        self._kbd.press('c')
        self._kbd.release('c')
        self._kbd.release(keyboard.Key.ctrl)

    def _capture_word(self, x: int, y: int):
        """
        Attempt to read the word the user double-clicked / long-pressed on.

        Step 1 — UI Automation (preferred)
          Give the OS a tiny moment to finish updating the selection after
          the double-click, then query UIA.  No clipboard is touched.

        Step 2 — Clipboard fallback
          If UIA returns nothing (app does not implement TextPattern), save
          the clipboard, simulate Ctrl+C, read the result, and restore
          the original clipboard content before returning.

        Step 3 — Validate
          Accept only genuine single words.  Sentences, URLs, and anything
          with whitespace are silently dropped — this is what prevents the
          "user selects a sentence → popup fires" bug.
        """

        # ── Step 1: UI Automation ─────────────────────────────────────────────
        # Small sleep so the OS selection state is fully settled before we ask.
        time.sleep(0.05)
        text   = _get_selected_text_uia()
        source = "UIA"

        # ── Step 2: Clipboard fallback ────────────────────────────────────────
        if not text:
            text   = _get_selected_text_clipboard_fallback(self._simulate_ctrl_c)
            source = "clipboard-fallback"

        # ── Step 3: Validate ──────────────────────────────────────────────────
        text = text.strip()

        if not _is_single_word(text):
            print(f"[LOG] Capture dropped ({source}) — not a single word: {repr(text)}", flush=True)
            return

        print(f"[LOG] Word captured via {source}: {text!r}", flush=True)
        self.word_queue.put((text, x, y))


# ════════════════════════════════════════════════════════════════════════════
# GlobalHotkeyWatcher
# ════════════════════════════════════════════════════════════════════════════

class GlobalHotkeyWatcher:
    """
    Listens for a double-press of Left Ctrl and fires `on_double_ctrl()`.

    Runs on its own daemon thread, completely independently of the mouse
    listener — so it works even when the mouse listener is paused/stopped,
    letting the user re-enable listening without touching the UI.

    Safety guard: if any non-Ctrl key is pressed between the two Ctrl
    presses (e.g. Ctrl+C … Ctrl+V), the double-press timer is reset so
    normal keyboard shortcuts never accidentally trigger a toggle.
    """

    DOUBLE_PRESS_THRESHOLD = 0.40   # seconds — window to count as double-press

    def __init__(self, on_double_ctrl):
        self._callback             = on_double_ctrl
        self._last_ctrl_time       = None
        self._had_intervening_key  = False
        self._listener             = None
        self._lock                 = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        if self._listener and self._listener.running:
            return
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.daemon = True
        self._listener.start()
        print("[HOTKEY] GlobalHotkeyWatcher started (double Left-Ctrl → toggle)", flush=True)

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
        print("[HOTKEY] GlobalHotkeyWatcher stopped", flush=True)

    def is_running(self) -> bool:
        return self._listener is not None and self._listener.running

    # ── Key handler ───────────────────────────────────────────────────────────

    def _on_key_press(self, key):
        if key == keyboard.Key.ctrl_l:
            now = time.time()
            with self._lock:
                last                      = self._last_ctrl_time
                intervening               = self._had_intervening_key
                self._last_ctrl_time      = now
                self._had_intervening_key = False   # reset for the next window

            if last and (now - last) < self.DOUBLE_PRESS_THRESHOLD and not intervening:
                # Genuine double-press with no other keys in between — reset
                # the timer so a third press doesn't instantly re-trigger.
                with self._lock:
                    self._last_ctrl_time = None
                print("[HOTKEY] Double Left-Ctrl detected — firing toggle", flush=True)
                threading.Thread(target=self._callback, daemon=True).start()
        else:
            # Any non-Ctrl key between two Ctrl presses → not a hotkey
            with self._lock:
                self._had_intervening_key = True