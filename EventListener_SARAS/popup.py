from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QSpacerItem, QSizePolicy, QApplication, QScrollArea
)
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtCore import Qt, QTimer
import sys

# Color palette — beach & white
BG_COLOR       = "rgba(255, 251, 245, 0.92)"   # warm off-white, slightly translucent
BORDER_COLOR   = "rgba(210, 195, 175, 0.6)"     # warm sand border
TEXT_PRIMARY   = "#1a1410"                       # near-black with warm tint
TEXT_SECONDARY = "#6b5c4a"                       # muted warm brown
TEXT_ITALIC    = "#8a7260"                       # softer warm for example
DIVIDER        = "rgba(180, 160, 130, 0.35)"    # subtle sand line
HEADER_COLOR   = "#9a7f5e"                       # warm tan for "Dictionary" label


class Popup(QWidget):
    def __init__(self, word, meaning, example, synonyms):
        super().__init__()
        self.setWindowTitle("SARAS - Product by ENGIN.E")
        self.setFixedSize(450, 350)
        self.setWindowOpacity(0.97)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Outer shell with rounded corners + shadow feel
        self.setStyleSheet(f"""
            QWidget#shell {{
                background-color: {BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 18px;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QWidget#content {{
                background: transparent;
            }}
        """)

        shell = QWidget(self)
        shell.setObjectName("shell")
        shell.setFixedSize(450, 350)

        # Scroll Area Setup
        scroll = QScrollArea(shell)
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(450, 350)

        # Inner content widget
        content = QWidget()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Font — DM Sans (clean, humanist, closest free match to Claude's font)
        FONT_FAMILY = "DM Sans"
        FONT_FALLBACK = "Helvetica Neue"

        def label_font(size, italic=False, weight=QFont.Weight.Normal):
            f = QFont(FONT_FAMILY, size)
            f.setItalic(italic)
            f.setWeight(weight)
            f.setStyleHint(QFont.StyleHint.SansSerif)
            return f

        # "Dictionary" header label
        dict_label = QLabel("Dictionary")
        dict_label.setFont(label_font(11, weight=QFont.Weight.Medium))
        dict_label.setStyleSheet(f"color: {HEADER_COLOR}; letter-spacing: 1.5px; text-transform: uppercase;")
        dict_label.setWordWrap(True)
        layout.addWidget(dict_label)

        # Thin divider
        def make_divider():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFixedHeight(1)
            line.setStyleSheet(f"background-color: {DIVIDER}; border: none;")
            return line

        layout.addWidget(make_divider())

        # Word
        word_label = QLabel(word)
        word_label.setFont(label_font(22, weight=QFont.Weight.Bold))
        word_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        word_label.setWordWrap(True)
        layout.addWidget(word_label)

        # Meaning
        meaning_label = QLabel(meaning)
        meaning_label.setFont(label_font(14))
        meaning_label.setStyleSheet(f"color: {TEXT_PRIMARY}; line-height: 1.5;")
        meaning_label.setWordWrap(True)
        layout.addWidget(meaning_label)

        # Example
        example_label = QLabel(example)
        example_label.setFont(label_font(13, italic=True))
        example_label.setStyleSheet(f"color: {TEXT_ITALIC};")
        example_label.setWordWrap(True)
        layout.addWidget(example_label)

        # Spacer
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        layout.addWidget(make_divider())

        # "Synonyms" label
        syn_label = QLabel("Synonyms")
        syn_label.setFont(label_font(11, weight=QFont.Weight.Medium))
        syn_label.setStyleSheet(f"color: {HEADER_COLOR}; letter-spacing: 1.5px;")
        syn_label.setWordWrap(True)
        layout.addWidget(syn_label)

        # Synonyms content
        synonyms_label = QLabel(synonyms)
        synonyms_label.setFont(label_font(13))
        synonyms_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        synonyms_label.setWordWrap(True)
        layout.addWidget(synonyms_label)

        layout.addStretch()

        # Set scroll content
        scroll.setWidget(content)

        QTimer.singleShot(8000, self.close)


# Function to show popup (test)
def show_popup(word, meaning, example, synonyms):
    app = QApplication(sys.argv)
    popup = Popup(word, meaning, example, synonyms)
    popup.show()
    popup.activateWindow()
    popup.raise_()
    sys.exit(app.exec())

# Uncomment to test it standalone
# show_popup(
#     "running",
#     "the act of administering or being in charge of something",
#     '"he has responsibility for the running of two companies at the same time."',
#     "management, control, supervision, operation"
# )