from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QSpacerItem, QSizePolicy, QApplication, QScrollArea
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import sys

class Popup(QWidget):
    def __init__(self, word, meaning, example, synonyms):
        super().__init__()
        self.setWindowTitle("SARAS - Product by ENGIN.E")
        self.setFixedSize(450, 350)
        self.setStyleSheet("background-color: #000000;")
        self.setWindowOpacity(0.9)

        # Scroll Area Setup
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")  # Optional: cleaner look

        # Inner content widget
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)

        # Dictionary Label
        dict_label = QLabel("Dictionary ───────────────────────────")
        dict_label.setFont(QFont("Georgia", 16))
        dict_label.setStyleSheet("color: white;")
        dict_label.setWordWrap(True)
        layout.addWidget(dict_label)

        # Word with horizontal line
        layout_word = QHBoxLayout()
        word_label = QLabel(word)
        word_label.setFont(QFont("AppleGothic", 18))
        word_label.setStyleSheet("color: white;")
        word_label.setWordWrap(True)
        layout_word.addWidget(word_label)

        side_line = QFrame()
        side_line.setFrameShape(QFrame.Shape.HLine)
        side_line.setFixedHeight(1)
        side_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.3);")
        layout_word.addWidget(side_line)
        layout.addLayout(layout_word)

        # Meaning
        meaning_label = QLabel(meaning)
        meaning_label.setFont(QFont("Georgia", 16))
        meaning_label.setStyleSheet("color: white;")
        meaning_label.setWordWrap(True)
        layout.addWidget(meaning_label)

        # Example
        example_label = QLabel(example)
        example_label.setFont(QFont("Georgia", 16, -1, italic=True))
        example_label.setStyleSheet("color: white;")
        example_label.setWordWrap(True)
        layout.addWidget(example_label)

        # Spacer
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Synonyms with line
        layout_syn = QHBoxLayout()
        syn_label = QLabel("Synonyms")
        syn_label.setFont(QFont("AppleGothic", 16))
        syn_label.setStyleSheet("color: white;")
        syn_label.setWordWrap(True)
        layout_syn.addWidget(syn_label)

        side_line2 = QFrame()
        side_line2.setFrameShape(QFrame.Shape.HLine)
        side_line2.setFixedHeight(1)
        side_line2.setStyleSheet("background-color: rgba(255, 255, 255, 0.3);")
        layout_syn.addWidget(side_line2)
        layout.addLayout(layout_syn)

        # Synonyms content
        synonyms_label = QLabel(synonyms)
        synonyms_label.setFont(QFont("Georgia", 16))
        synonyms_label.setStyleSheet("color: white;")
        synonyms_label.setWordWrap(True)
        layout.addWidget(synonyms_label)

        # Bottom Line
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.Shape.HLine)
        bottom_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.3);")
        layout.addWidget(bottom_line)

        # Set scroll content
        scroll.setWidget(content)

        # Main layout for window
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

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
