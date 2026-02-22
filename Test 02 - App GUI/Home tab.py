"""
Saras - Dictionary App UI
PyQt6 | Version 0.1
White & Beige Premium Theme
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QCheckBox,
    QComboBox, QStackedWidget, QGraphicsDropShadowEffect, QSizePolicy,
    QSpacerItem, QTextEdit
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QCursor, QPixmap, QPainter, QBrush, QPen


# ─────────────────────────────────────────
#  PALETTE & TOKENS
# ─────────────────────────────────────────
class Theme:
    BG          = "#FAF8F5"       # warm off-white
    SURFACE     = "#FFFFFF"
    CARD        = "#F5F2ED"       # warm beige card
    BORDER      = "#E8E2D9"
    ACCENT      = "#2D2926"       # rich espresso
    ACCENT_SOFT = "#6B5E52"       # muted brown
    TEXT        = "#1A1612"
    TEXT_SUB    = "#8C7B6E"
    TEXT_MUTED  = "#B5A99D"
    HIGHLIGHT   = "#C9A96E"       # warm gold
    HIGHLIGHT_LT= "#F0E6D3"      # light gold tint
    DANGER      = "#C0392B"
    SUCCESS     = "#27AE60"
    RADIUS      = "10px"
    RADIUS_LG   = "14px"


# ─────────────────────────────────────────
#  GLOBAL STYLESHEET
# ─────────────────────────────────────────
STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {Theme.BG};
    color: {Theme.TEXT};
    font-family: 'Georgia', 'Palatino Linotype', 'Book Antiqua', serif;
}}

/* ── SIDEBAR NAV ── */
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
    font-weight: 500;
    color: {Theme.ACCENT_SOFT};
}}
#NavButton:hover {{
    background-color: {Theme.CARD};
    color: {Theme.TEXT};
}}
#NavButton[active="true"] {{
    background-color: {Theme.HIGHLIGHT_LT};
    color: {Theme.ACCENT};
    font-weight: 600;
}}

/* ── TOP BAR ── */
#TopBar {{
    background-color: {Theme.SURFACE};
    border-bottom: 1px solid {Theme.BORDER};
    padding: 0 24px;
    min-height: 60px;
    max-height: 60px;
}}

/* ── SEARCH ── */
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
    outline: none;
}}

/* ── SEARCH BUTTON ── */
#SearchBtn {{
    background-color: {Theme.ACCENT};
    color: white;
    border: none;
    border-radius: {Theme.RADIUS};
    padding: 12px 22px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
#SearchBtn:hover {{
    background-color: {Theme.ACCENT_SOFT};
}}
#SearchBtn:pressed {{
    background-color: {Theme.HIGHLIGHT};
}}

/* ── CARDS ── */
#Card {{
    background-color: {Theme.SURFACE};
    border: 1px solid {Theme.BORDER};
    border-radius: {Theme.RADIUS_LG};
    padding: 20px;
}}

/* ── WORD CHIP ── */
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

/* ── SECTION TITLE ── */
#SectionTitle {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: {Theme.TEXT_MUTED};
    text-transform: uppercase;
}}

/* ── SETTINGS CONTROLS ── */
QComboBox {{
    background-color: {Theme.CARD};
    border: 1.5px solid {Theme.BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: {Theme.TEXT};
    min-width: 200px;
}}
QComboBox:hover {{
    border-color: {Theme.HIGHLIGHT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {Theme.SURFACE};
    border: 1px solid {Theme.BORDER};
    selection-background-color: {Theme.HIGHLIGHT_LT};
    selection-color: {Theme.ACCENT};
    border-radius: 8px;
    padding: 4px;
}}

QCheckBox {{
    font-size: 13px;
    color: {Theme.TEXT};
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {Theme.BORDER};
    border-radius: 5px;
    background-color: {Theme.CARD};
}}
QCheckBox::indicator:checked {{
    background-color: {Theme.ACCENT};
    border-color: {Theme.ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {Theme.HIGHLIGHT};
}}

/* ── SCROLLBAR ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {Theme.BORDER};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ── SECONDARY BTN ── */
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

/* ── GOLD BTN ── */
#GoldBtn {{
    background-color: {Theme.HIGHLIGHT};
    color: {Theme.SURFACE};
    border: none;
    border-radius: {Theme.RADIUS};
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
}}
#GoldBtn:hover {{
    background-color: #B8945A;
}}

/* ── STAT BADGE ── */
#StatBadge {{
    background-color: {Theme.HIGHLIGHT_LT};
    color: {Theme.HIGHLIGHT};
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}

/* ── DIVIDER ── */
#Divider {{
    background-color: {Theme.BORDER};
    max-height: 1px;
    min-height: 1px;
}}

/* ── EMAIL LINK ── */
#LinkLabel {{
    color: {Theme.HIGHLIGHT};
    font-size: 13px;
    text-decoration: underline;
}}
"""


# ─────────────────────────────────────────
#  HELPER WIDGETS
# ─────────────────────────────────────────
def label(text, size=13, weight=400, color=None, obj_name=None):
    lbl = QLabel(text)
    # Use Georgia (Claude's warm serif) — fallback to Palatino → Times New Roman
    f = QFont()
    f.setFamilies(["Georgia", "Palatino Linotype", "Book Antiqua", "Times New Roman", "serif"])
    f.setPointSize(size)
    f.setWeight(QFont.Weight.Bold if weight >= 700 else
                QFont.Weight.DemiBold if weight >= 600 else
                QFont.Weight.Medium if weight >= 500 else
                QFont.Weight.Normal)
    lbl.setFont(f)
    if color:
        lbl.setStyleSheet(f"color: {color};")
    if obj_name:
        lbl.setObjectName(obj_name)
    return lbl


def divider():
    d = QFrame()
    d.setObjectName("Divider")
    d.setFrameShape(QFrame.Shape.HLine)
    return d


def shadow(widget, blur=20, offset=(0, 4), color="#00000015"):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setOffset(*offset)
    eff.setColor(QColor(color))
    widget.setGraphicsEffect(eff)
    return eff


# ─────────────────────────────────────────
#  NAV BUTTON
# ─────────────────────────────────────────
class NavButton(QPushButton):
    def __init__(self, icon_char, text, parent=None):
        super().__init__(f"  {icon_char}   {text}", parent)
        self.setObjectName("NavButton")
        self.setCheckable(False)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(42)
        self._active = False

    def set_active(self, val: bool):
        self._active = val
        self.setProperty("active", "true" if val else "false")
        self.style().unpolish(self)
        self.style().polish(self)


# ─────────────────────────────────────────
#  PAGE: HOME
# ─────────────────────────────────────────
class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        # ── greeting
        greet = label("Good morning 👋", 22, 700, Theme.TEXT)
        sub   = label("What word are you looking up today?", 13, 400, Theme.TEXT_SUB)
        root.addWidget(greet)
        root.addWidget(sub)

        # ── search bar row
        search_card = QWidget()
        search_card.setObjectName("Card")
        sc_lay = QHBoxLayout(search_card)
        sc_lay.setContentsMargins(4, 4, 4, 4)
        sc_lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setObjectName("SearchBar")
        self.search.setPlaceholderText("Search a word…")
        self.search.setMinimumHeight(46)

        btn = QPushButton("Look up")
        btn.setObjectName("SearchBtn")
        btn.setMinimumHeight(46)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        sc_lay.addWidget(self.search)
        sc_lay.addWidget(btn)
        shadow(search_card, blur=24, offset=(0, 6), color="#0000000A")
        root.addWidget(search_card)

        # ── stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        for value, caption in [("47", "Words Today"), ("312", "This Week"), ("50", "History Limit")]:
            stat = self._stat_card(value, caption)
            stats_row.addWidget(stat)

        root.addLayout(stats_row)

        # ── recent history
        root.addWidget(label("RECENT LOOKUPS", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        chip_container = QWidget()
        chip_lay = FlowLayout(chip_container)
        chip_lay.setSpacing(8)

        sample_words = [
            "ephemeral", "serendipity", "eloquent", "luminous", "tenacious",
            "paradox", "resilience", "ambiguous", "clarity", "benevolent",
            "nostalgia", "labyrinth", "vivid", "profound", "intricate",
            "wanderlust", "euphoria", "solace", "cogent", "melancholy",
            "perspicacious", "ethereal", "sublime", "catharsis", "languid",
        ]

        for w in sample_words:
            chip = QPushButton(w)
            chip.setObjectName("WordChip")
            chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            chip_lay.addWidget(chip)

        scroll.setWidget(chip_container)
        scroll.setMinimumHeight(140)

        root.addWidget(scroll)
        root.addStretch()

        info = label("You looked up 47 words today  ·  3 words away from your daily record", 11, 400, Theme.TEXT_MUTED)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(info)

    def _stat_card(self, value, caption):
        card = QWidget()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(4)

        v = label(value, 28, 700, Theme.ACCENT)
        c = label(caption, 11, 500, Theme.TEXT_MUTED)
        lay.addWidget(v)
        lay.addWidget(c)
        shadow(card, blur=16, offset=(0, 3), color="#0000000A")
        return card


# ─────────────────────────────────────────
#  PAGE: HISTORY
# ─────────────────────────────────────────
class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(20)

        hdr = QHBoxLayout()
        hdr.addWidget(label("History", 22, 700, Theme.TEXT))
        hdr.addStretch()
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        hdr.addWidget(clear_btn)
        root.addLayout(hdr)

        sub = label("Your last 50 lookups are saved locally.", 13, 400, Theme.TEXT_SUB)
        root.addWidget(sub)
        root.addWidget(divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(8)

        words = [
            ("ephemeral", "adj.", "Today, 2:41 PM"),
            ("serendipity", "noun", "Today, 1:05 PM"),
            ("eloquent", "adj.", "Today, 11:32 AM"),
            ("tenacious", "adj.", "Today, 10:17 AM"),
            ("paradox", "noun", "Today, 9:48 AM"),
            ("resilience", "noun", "Yesterday, 7:22 PM"),
            ("ambiguous", "adj.", "Yesterday, 3:55 PM"),
            ("clarity", "noun", "Yesterday, 2:10 PM"),
            ("luminous", "adj.", "Yesterday, 12:00 PM"),
            ("benevolent", "adj.", "Yesterday, 9:05 AM"),
            ("nostalgia", "noun", "Mon, Feb 20"),
            ("labyrinth", "noun", "Mon, Feb 20"),
            ("vivid", "adj.", "Mon, Feb 20"),
        ]

        for word, pos, time_ in words:
            row = self._history_row(word, pos, time_)
            c_lay.addWidget(row)

        c_lay.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)

    def _history_row(self, word, pos, time_):
        row = QWidget()
        row.setObjectName("Card")
        row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        lay = QHBoxLayout(row)
        lay.setContentsMargins(16, 12, 16, 12)

        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(label(word, 14, 600, Theme.TEXT))
        left.addWidget(label(pos, 11, 400, Theme.TEXT_MUTED))

        lay.addLayout(left)
        lay.addStretch()
        lay.addWidget(label(time_, 11, 400, Theme.TEXT_MUTED))
        return row


# ─────────────────────────────────────────
#  PAGE: SETTINGS
# ─────────────────────────────────────────
class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(28)

        root.addWidget(label("Settings", 22, 700, Theme.TEXT))
        root.addWidget(label("Customize how Saras works for you.", 13, 400, Theme.TEXT_SUB))

        # ── Trigger
        root.addWidget(self._section("ACTIVATION TRIGGER"))
        root.addWidget(self._setting_row(
            "Trigger Method",
            "How you activate Saras while reading.",
            self._combo(["Double-click", "Ctrl + Double-click", "Middle-click", "Ctrl + Shift"])
        ))

        # ── Startup
        root.addWidget(self._section("SYSTEM"))
        root.addWidget(self._setting_row(
            "Start with Windows",
            "Launch Saras automatically when you log in.",
            self._checkbox("Enable startup")
        ))

        # ── Theme
        root.addWidget(self._section("APPEARANCE"))
        root.addWidget(self._setting_row(
            "Theme",
            "Choose between light and dark interface.",
            self._combo(["Light (Default)", "Dark"])
        ))

        save_btn = QPushButton("Save Preferences")
        save_btn.setObjectName("SearchBtn")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setMaximumWidth(200)
        save_btn.setMinimumHeight(42)
        root.addWidget(save_btn)
        root.addStretch()

    def _section(self, text):
        return label(text, 10, 700, Theme.TEXT_MUTED, "SectionTitle")

    def _combo(self, options):
        cb = QComboBox()
        for o in options:
            cb.addItem(o)
        cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return cb

    def _checkbox(self, text):
        cb = QCheckBox(text)
        return cb

    def _setting_row(self, title, subtitle, control):
        row = QWidget()
        row.setObjectName("Card")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.addWidget(label(title, 13, 600, Theme.TEXT))
        text_col.addWidget(label(subtitle, 11, 400, Theme.TEXT_MUTED))

        lay.addLayout(text_col, stretch=1)
        lay.addWidget(control)
        return row


# ─────────────────────────────────────────
#  PAGE: SUPPORT & FEEDBACK
# ─────────────────────────────────────────
class SupportPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(20)

        root.addWidget(label("Support & Feedback", 22, 700, Theme.TEXT))
        root.addWidget(label("We're here to help. Reach out any time.", 13, 400, Theme.TEXT_SUB))
        root.addWidget(divider())

        # ── Email card
        email_card = QWidget()
        email_card.setObjectName("Card")
        ec_lay = QHBoxLayout(email_card)
        ec_lay.setContentsMargins(20, 18, 20, 18)

        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(label("Email Support", 13, 600, Theme.TEXT))
        left.addWidget(label("udhyog@saras.app", 12, 400, Theme.HIGHLIGHT, "LinkLabel"))

        ec_lay.addLayout(left)
        ec_lay.addStretch()

        mailto_btn = QPushButton("Send Email")
        mailto_btn.setObjectName("GoldBtn")
        mailto_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        mailto_btn.setMinimumHeight(38)
        ec_lay.addWidget(mailto_btn)
        root.addWidget(email_card)

        # ── Feedback card
        fb_card = QWidget()
        fb_card.setObjectName("Card")
        fb_lay = QHBoxLayout(fb_card)
        fb_lay.setContentsMargins(20, 18, 20, 18)

        left2 = QVBoxLayout()
        left2.setSpacing(4)
        left2.addWidget(label("Send Feedback", 13, 600, Theme.TEXT))
        left2.addWidget(label("Share your thoughts to help us improve Saras.", 11, 400, Theme.TEXT_MUTED))

        fb_lay.addLayout(left2)
        fb_lay.addStretch()

        fb_btn = QPushButton("Open Form")
        fb_btn.setObjectName("SecondaryBtn")
        fb_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        fb_btn.setMinimumHeight(38)
        fb_lay.addWidget(fb_btn)
        root.addWidget(fb_card)

        # ── Updates card
        upd_card = QWidget()
        upd_card.setObjectName("Card")
        upd_lay = QHBoxLayout(upd_card)
        upd_lay.setContentsMargins(20, 18, 20, 18)

        left3 = QVBoxLayout()
        left3.setSpacing(4)
        left3.addWidget(label("Check for Updates", 13, 600, Theme.TEXT))
        left3.addWidget(label("Current version: 0.1  ·  Checks GitHub Releases", 11, 400, Theme.TEXT_MUTED))

        upd_lay.addLayout(left3)
        upd_lay.addStretch()

        upd_btn = QPushButton("Check Now")
        upd_btn.setObjectName("SecondaryBtn")
        upd_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        upd_btn.setMinimumHeight(38)
        upd_lay.addWidget(upd_btn)
        root.addWidget(upd_card)

        root.addStretch()

        footer = label("Saras v0.1  ·  Made with care  ·  © 2026 Saras", 11, 400, Theme.TEXT_MUTED)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)


# ─────────────────────────────────────────
#  PAGE: ABOUT  (with greeting composer)
# ─────────────────────────────────────────

class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(20)

        # ── Header row
        root.addWidget(label("About Saras", 22, 700, Theme.TEXT))
        root.addWidget(label("Version 0.1  ·  Early Access", 12, 400, Theme.TEXT_MUTED))
        root.addWidget(divider())

        # ── App blurb card
        blurb_card = QWidget()
        blurb_card.setObjectName("Card")
        bc_lay = QVBoxLayout(blurb_card)
        bc_lay.setContentsMargins(24, 20, 24, 20)
        bc_lay.setSpacing(6)

        bc_lay.addWidget(label("Saras.", 28, 700, Theme.ACCENT))
        desc = label(
            "Saras brings instant word definitions to your fingertips,\n"
            "wherever you're reading — quietly running in the background.",
            13, 400, Theme.TEXT_SUB
        )
        desc.setWordWrap(True)
        bc_lay.addWidget(desc)
        shadow(blurb_card, blur=16, offset=(0, 3), color="#0000000A")
        root.addWidget(blurb_card)

        # ── Greeting / message composer
        root.addWidget(label("SEND US A GREETING", 10, 700, Theme.TEXT_MUTED, "SectionTitle"))

        msg_card = QWidget()
        msg_card.setObjectName("Card")
        mc_lay = QVBoxLayout(msg_card)
        mc_lay.setContentsMargins(20, 18, 20, 18)
        mc_lay.setSpacing(12)

        prompt = label(
            "Have a thought, a kind word, or just want to say hello? We read every message. 🌿",
            12, 400, Theme.TEXT_SUB
        )
        prompt.setWordWrap(True)
        mc_lay.addWidget(prompt)

        self._msg_box = QTextEdit()
        self._msg_box.setPlaceholderText("Write your message here…  e.g. 'Hi, I love what you are building'!")
        self._msg_box.setMinimumHeight(100)
        self._msg_box.setMaximumHeight(130)
        self._msg_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.CARD};
                border: 1.5px solid {Theme.BORDER};
                border-radius: 10px;
                padding: 10px 14px;
                font-family: Georgia, serif;
                font-size: 13px;
                color: {Theme.TEXT};
            }}
            QTextEdit:focus {{
                border: 1.5px solid {Theme.HIGHLIGHT};
                background-color: {Theme.SURFACE};
            }}
        """)
        mc_lay.addWidget(self._msg_box)

        # name + send row
        name_row = QHBoxLayout()
        name_row.setSpacing(10)

        self._name_box = QLineEdit()
        self._name_box.setObjectName("SearchBar")
        self._name_box.setPlaceholderText("Your name (optional)")
        self._name_box.setMinimumHeight(40)
        self._name_box.setMaximumWidth(220)

        name_row.addWidget(self._name_box)
        name_row.addStretch()

        self._send_btn = QPushButton("Send Greeting ✉")
        self._send_btn.setObjectName("GoldBtn")
        self._send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._send_btn.setMinimumHeight(40)
        self._send_btn.clicked.connect(self._send_greeting)
        name_row.addWidget(self._send_btn)

        mc_lay.addLayout(name_row)

        # confirmation label (hidden by default)
        self._confirm_lbl = label("", 11, 500, Theme.SUCCESS)
        self._confirm_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._confirm_lbl.hide()
        mc_lay.addWidget(self._confirm_lbl)

        root.addWidget(msg_card)
        root.addStretch()

        footer = label("Built with ♡ for curious minds  ·  © 2026 Saras", 11, 400, Theme.TEXT_MUTED)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

    def _send_greeting(self):
        msg  = self._msg_box.toPlainText().strip()
        name = self._name_box.text().strip()
        if not msg:
            self._confirm_lbl.setText("✦ Please write a message first.")
            self._confirm_lbl.setStyleSheet(f"color: {Theme.DANGER};")
            self._confirm_lbl.show()
            return

        # Build mailto link and open in default mail client
        import urllib.parse, webbrowser
        greeting = f"From: {name}\n\n{msg}" if name else msg
        subject  = urllib.parse.quote("A Greeting from a Saras User")
        body     = urllib.parse.quote(greeting)
        webbrowser.open(f"mailto:udhyog@saras.app?subject={subject}&body={body}")

        self._confirm_lbl.setText("✦ Opening your mail client… Thank you for writing to us!")
        self._confirm_lbl.setStyleSheet(f"color: {Theme.SUCCESS};")
        self._confirm_lbl.show()
        self._send_btn.setEnabled(False)
        self._send_btn.setText("Sent ✓")

        # Reset after 5 seconds
        QTimer.singleShot(5000, self._reset_form)

    def _reset_form(self):
        self._msg_box.clear()
        self._name_box.clear()
        self._confirm_lbl.hide()
        self._send_btn.setEnabled(True)
        self._send_btn.setText("Send Greeting ✉")


# ─────────────────────────────────────────
#  FLOW LAYOUT (word chips)
# ─────────────────────────────────────────
from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtWidgets import QLayout

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def setSpacing(self, spacing):
        self._spacing = spacing

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test):
        m = self.contentsMargins()
        x, y = rect.x() + m.left(), rect.y() + m.top()
        line_h = 0

        for item in self._items:
            w = item.sizeHint()
            next_x = x + w.width() + self._spacing
            if next_x - self._spacing > rect.right() and line_h > 0:
                x = rect.x() + m.left()
                y += line_h + self._spacing
                next_x = x + w.width() + self._spacing
                line_h = 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), w))
            x = next_x
            line_h = max(line_h, w.height())

        return y + line_h - rect.y() + m.bottom()


# ─────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────
class SarasApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Saras · Dictionary")
        self.setMinimumSize(860, 600)
        self.resize(960, 660)

        # ── Window icon: place lotus_coin_v2.ico in the same folder as this script
        import os
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lotus_coin_v2.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback: draw a simple "S" letter icon programmatically
            pm = QPixmap(64, 64)
            pm.fill(QColor(Theme.ACCENT))
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#FFFFFF")))
            f = QFont("Georgia", 32, QFont.Weight.Bold)
            painter.setFont(f)
            painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "S")
            painter.end()
            self.setWindowIcon(QIcon(pm))

        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Top bar
        top_bar = self._top_bar()
        main_lay.addWidget(top_bar)

        # ── Body (sidebar + content)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        sidebar = self._sidebar()
        body.addWidget(sidebar)

        # content stack
        self.stack = QStackedWidget()
        self.stack.addWidget(HomePage())    # 0
        self.stack.addWidget(HistoryPage()) # 1
        self.stack.addWidget(SettingsPage())# 2
        self.stack.addWidget(SupportPage()) # 3
        self.stack.addWidget(AboutPage())   # 4
        body.addWidget(self.stack)

        main_lay.addLayout(body)

    def _top_bar(self):
        bar = QWidget()
        bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)

        logo = label("Saras.", 18, 700, Theme.ACCENT)
        ver  = label("v0.1", 10, 500, Theme.TEXT_MUTED)
        ver.setStyleSheet(f"""
            color: {Theme.TEXT_MUTED};
            background-color: {Theme.CARD};
            border-radius: 9px;
            padding: 2px 8px;
            font-size: 11px;
        """)

        lay.addWidget(logo)
        lay.addWidget(ver)
        lay.addStretch()

        pill = label("47 words today", 11, 500, Theme.HIGHLIGHT)
        pill.setStyleSheet(f"""
            color: {Theme.HIGHLIGHT};
            background-color: {Theme.HIGHLIGHT_LT};
            border-radius: 10px;
            padding: 4px 12px;
        """)
        lay.addWidget(pill)
        return bar

    def _sidebar(self):
        sb = QWidget()
        sb.setObjectName("Sidebar")
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(12, 20, 12, 20)
        lay.setSpacing(4)

        nav_items = [
            ("⌂", "Home",     0),
            ("◷", "History",  1),
            ("⚙", "Settings", 2),
            ("✉", "Support",  3),
            ("◉", "About",    4),
        ]

        self._nav_btns = []
        for icon, text, idx in nav_items:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda _, i=idx: self._nav(i))
            self._nav_btns.append(btn)
            lay.addWidget(btn)

        self._nav_btns[0].set_active(True)
        lay.addStretch()

        ver_lbl = label("Saras v0.1", 10, 400, Theme.TEXT_MUTED)
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ver_lbl)
        return sb

    def _nav(self, index):
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == index)
        self.stack.setCurrentIndex(index)


# ─────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    win = SarasApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()