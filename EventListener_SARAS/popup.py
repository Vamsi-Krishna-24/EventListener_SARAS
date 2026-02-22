from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QSpacerItem, QSizePolicy, QApplication, QScrollArea, QPushButton
)
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt, QTimer
import sys

# ── Palette ────────────────────────────────────────────────
BG_COLOR       = "rgba(255, 255, 255, 0.96)"   # clean white, barely translucent
BORDER_COLOR   = "rgba(220, 200, 170, 0.7)"    # warm sand rim
TEXT_PRIMARY   = "#1c1209"                      # rich warm black
TEXT_SECONDARY = "#7a6550"                      # warm mid-brown
TEXT_ITALIC    = "#a08c72"                      # soft caramel for example
DIVIDER        = "rgba(200, 175, 140, 0.4)"    # light sand divider
HEADER_COLOR   = "#b8956a"                      # golden sand — warm but vivid
CLOSE_BG       = "rgba(200, 175, 140, 0.25)"   # subtle sand pill


class Popup(QWidget):
    def __init__(self, word, meaning, example, synonyms):
        super().__init__()
        self.setWindowTitle("SARAS - Product by ENGIN.E")
        self.setFixedSize(450, 350)
        self.setWindowOpacity(0.98)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── Shell (rounded card) ───────────────────────────
        self.setStyleSheet(f"""
            QWidget#shell {{
                background-color: {BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 20px;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QWidget#content {{
                background: transparent;
            }}
            QPushButton#close_btn {{
                background-color: {CLOSE_BG};
                color: {TEXT_SECONDARY};
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 500;
                padding: 0px;
            }}
            QPushButton#close_btn:hover {{
                background-color: rgba(180, 100, 80, 0.18);
                color: #b85a3a;
            }}
        """)

        shell = QWidget(self)
        shell.setObjectName("shell")
        shell.setFixedSize(450, 350)

        # ── Scroll Area ────────────────────────────────────
        scroll = QScrollArea(shell)
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(450, 350)

        content = QWidget()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(12)

        # ── Font helper ────────────────────────────────────
        def lf(size, italic=False, weight=QFont.Weight.Normal):
            f = QFont("DM Sans", size)
            f.setItalic(italic)
            f.setWeight(weight)
            f.setStyleHint(QFont.StyleHint.SansSerif)
            return f

        def divider():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFixedHeight(1)
            line.setStyleSheet(f"background-color: {DIVIDER}; border: none;")
            return line

        # ── Top row: "DICTIONARY" + close button ──────────
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        dict_label = QLabel("DICTIONARY")
        dict_label.setFont(lf(10, weight=QFont.Weight.Medium))
        dict_label.setStyleSheet(f"color: {HEADER_COLOR}; letter-spacing: 2px;")
        top_row.addWidget(dict_label)

        top_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn)

        layout.addLayout(top_row)
        layout.addWidget(divider())

        # ── Word ───────────────────────────────────────────
        word_label = QLabel(word)
        word_label.setFont(lf(26, weight=QFont.Weight.Bold))
        word_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        word_label.setWordWrap(True)
        layout.addWidget(word_label)

        # ── Meaning ────────────────────────────────────────
        meaning_label = QLabel(meaning)
        meaning_label.setFont(lf(14))
        meaning_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        meaning_label.setWordWrap(True)
        layout.addWidget(meaning_label)

        # ── Example ────────────────────────────────────────
        example_label = QLabel(example)
        example_label.setFont(lf(13, italic=True))
        example_label.setStyleSheet(f"color: {TEXT_ITALIC};")
        example_label.setWordWrap(True)
        layout.addWidget(example_label)

        layout.addItem(QSpacerItem(10, 6, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addWidget(divider())

        # ── Synonyms ───────────────────────────────────────
        syn_header = QLabel("SYNONYMS")
        syn_header.setFont(lf(10, weight=QFont.Weight.Medium))
        syn_header.setStyleSheet(f"color: {HEADER_COLOR}; letter-spacing: 2px;")
        layout.addWidget(syn_header)

        synonyms_label = QLabel(synonyms)
        synonyms_label.setFont(lf(13))
        synonyms_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        synonyms_label.setWordWrap(True)
        layout.addWidget(synonyms_label)

        layout.addStretch()

        scroll.setWidget(content)
        QTimer.singleShot(8000, self.close)


def show_popup(word, meaning, example, synonyms):
    app = QApplication(sys.argv)
    popup = Popup(word, meaning, example, synonyms)
    popup.show()
    popup.activateWindow()
    popup.raise_()
    sys.exit(app.exec())

# show_popup(
#     "running",
#     "the act of administering or being in charge of something",
#     '"he was responsible for the running of two companies at once."',
#     "management, control, supervision, operation"
# )