import os
from typing import Optional
from datetime import datetime
import logging  # <-- Add logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QSpinBox, QLineEdit, QPushButton,
    QDialogButtonBox, QFileDialog
)
from PyQt5.QtGui import QFont

class ReminderSettingsDialog(QDialog):
    def __init__(self, enabled, minutes, audio, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reminder Settings")
        self.setFixedSize(400, 200)

        arial_font = QFont("Arial", 12)
        self.setFont(arial_font)

        # restore incoming values
        self.enabled = enabled
        self.minutes = minutes
        self.audio   = audio

        self.init_ui()

    def init_ui(self):
        arial_font = QFont("Arial", 12)
        layout = QVBoxLayout(self)

        # Enable checkbox
        self.enable_chk = QCheckBox("Enable Reminders")
        self.enable_chk.setFont(arial_font)
        self.enable_chk.setChecked(self.enabled)
        layout.addWidget(self.enable_chk)

        # Minutes spin
        row1 = QHBoxLayout()
        lbl1 = QLabel("Minutes before hour:")
        lbl1.setFont(arial_font)
        row1.addWidget(lbl1)
        self.minute_spin = QSpinBox()
        self.minute_spin.setFont(arial_font)
        self.minute_spin.setRange(1, 59)
        self.minute_spin.setValue(self.minutes)
        row1.addWidget(self.minute_spin)
        layout.addLayout(row1)

        # Audio file selector
        row2 = QHBoxLayout()
        lbl2 = QLabel("Reminder sound:")
        lbl2.setFont(arial_font)
        row2.addWidget(lbl2)
        self.audio_edit = QLineEdit(self.audio)
        self.audio_edit.setFont(arial_font)
        row2.addWidget(self.audio_edit, 1)
        btn = QPushButton("Browse…")
        btn.setFont(arial_font)
        btn.clicked.connect(self.select_audio_file)
        row2.addWidget(btn)
        layout.addLayout(row2)

        # OK / Cancel
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.setFont(arial_font)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def select_audio_file(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.wav *.mp3)"
        )
        if fp:
            self.audio_edit.setText(fp)
            logging.info(f"User selected reminder audio file: {fp}")

    def getSettings(self):
        enabled = self.enable_chk.isChecked()
        minutes = self.minute_spin.value()
        audio = self.audio_edit.text()
        logging.info(f"Reminder settings dialog returned: enabled={enabled}, minutes={minutes}, audio={audio}")
        return (
            enabled,
            minutes,
            audio
        )

def set_reminder(message: str, time: datetime, recurring: Optional[int] = None):
    """Set a reminder with optional recurrence in minutes."""
    # ...implementation...
