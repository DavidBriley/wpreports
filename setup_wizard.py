from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox
from PyQt5.QtGui import QFont
import logging  # <-- Add logging

class SetupWizard(QDialog):
    def __init__(self, current_base_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setup Wizard")
        self.setMinimumSize(420, 180)  # Allow dialog to expand as needed
        self.base_dir = current_base_dir

        arial_font = QFont("Arial", 12)
        self.setFont(arial_font)

        layout = QVBoxLayout(self)
        label = QLabel("Choose the folder where reports and templates will be saved:")
        label.setWordWrap(True)
        label.setFont(arial_font)
        layout.addWidget(label)

        self.dir_edit = QLineEdit(self.base_dir)
        self.dir_edit.setFont(arial_font)
        layout.addWidget(self.dir_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFont(arial_font)
        browse_btn.clicked.connect(self.browse)
        layout.addWidget(browse_btn)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.setFont(arial_font)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def browse(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Reports Folder", self.dir_edit.text())
        if dir_path:
            self.dir_edit.setText(dir_path)
            logging.info(f"User browsed and selected reports folder: {dir_path}")

    def get_base_dir(self):
        base_dir = self.dir_edit.text().strip()
        logging.info(f"SetupWizard returning base_dir: {base_dir}")
        return base_dir
