import sys
import os
import datetime
import shutil
import json
import logging  # <-- Add logging
import hashlib
import subprocess            # <— add

from PyQt5.QtWidgets    import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QStyleFactory, QMessageBox, QFileDialog, QDialog, QAction, QStatusBar, QInputDialog,
    QScrollArea, QDialog, QLabel, QPushButton, QSizePolicy,
    QLineEdit  # <-- Add this import
)
from PyQt5.QtGui        import QIcon, QFont, QPalette, QColor, QDesktopServices  # <— add QDesktopServices
from PyQt5.QtCore       import Qt, QTimer, QUrl, QDate
from PyQt5.QtMultimedia import QSoundEffect

from config           import load_config, save_config
from utils            import resource_path, create_desktop_shortcut
from reminders        import ReminderSettingsDialog
from report_generator import create_hourly, create_shift
from ui_builder       import build_body_ui
from setup_wizard     import SetupWizard  # Add this import


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup logging FIRST so it's available everywhere
        self.logger = logging.getLogger("WPReports")

        # — Load & restore config —
        self.load_config()
        self.base_dir            = self.config.get("base_dir", "")
        self.template_path       = self.config.get("template_path", "")
        self.shift_template_path = self.config.get("shift_template_path", "")
        self.reminder_enabled    = self.config.get("reminder_enabled", True)
        self.reminder_minutes    = self.config.get("reminder_minutes", 5)
        self.reminder_audio      = self.config.get("reminder_audio", "reminder.wav")
        self.last_reminder_hour  = None
        self.font_size           = self.config.get("font_size", 16)
        self.window_width        = self.config.get("window_width", 600)
        self.window_height       = self.config.get("window_height", 600)
        self.dark_mode           = self.config.get("dark_mode", False)

        # Show setup wizard if config is missing or base_dir is not set
        if not self.base_dir or not os.path.isdir(self.base_dir):
            self.run_setup_wizard()

        # — Window flags & icon —
        self.setWindowTitle("Wet Plant Reports")
        icon_path = resource_path("Raven_icon.ico")
        self.setWindowIcon(QIcon(icon_path))

        # Set initial size and allow resizing
        self.resize(self.window_width, self.window_height)
        self.setMinimumSize(600, 600)

        # — Standard central widget layout —
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        build_body_ui(self, layout)
        central.setLayout(layout)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        # — Menus, timers & theme —
        self.init_menu()
        self.setup_menu_bar()
        self.init_help_menu()  # Add this line

        # Customize the menu bar font
        mb = self.menuBar()
        font = mb.font()
        font.setPointSize(12)  # Set font size
        font.setFamily("Arial")  # Set font family to Arial
        mb.setFont(font)

        self.init_timers()
        self.apply_theme()
        self.apply_font_size()

        # — Status bar —
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.logger.info("Application started")

        # Ensure admin password hash exists in config
        if "admin_pw_hash" not in self.config:
            self._set_admin_password()

    def toggleMaxRestore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.logger.info("Window toggled maximize/restore")

    def init_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        # Remove Set Reports Folder action
        # set_folder_action = QAction("Set Reports Folder…", self)
        # set_folder_action.triggered.connect(self.set_reports_folder)
        # file_menu.addAction(set_folder_action)
        # Add Setup Wizard menu item
        setup_wizard_action = QAction("Setup Wizard…", self)
        setup_wizard_action.triggered.connect(self.run_setup_wizard)
        file_menu.addAction(setup_wizard_action)

        # Add "Open Report..." action using QFileDialog
        open_report_action = QAction("Open Report...", self)
        open_report_action.triggered.connect(self.open_report_file_dialog)
        file_menu.addAction(open_report_action)

    def open_report_file_dialog(self):
        """
        Open a QFileDialog to select and open a report file.
        """
        start_dir = os.path.join(self.base_dir, "Wet Plant Reports")
        font = QFont("Arial", self.font_size)
        dlg = QFileDialog(self)
        dlg.setWindowTitle("Open Report File")
        dlg.setDirectory(start_dir)
        dlg.setNameFilters(["Excel Files (*.xlsx *.xls)", "All Files (*)"])
        dlg.setFont(font)
        if dlg.exec_() == QFileDialog.Accepted:
            fp = dlg.selectedFiles()[0]
            if fp and os.path.isfile(fp):
                self.logger.info(f"User opened report file: {fp}")
                os.startfile(fp)

    def set_reports_folder(self):
        font = QFont("Arial", self.font_size)
        dlg = QFileDialog(self)
        dlg.setWindowTitle("Select Reports Folder")
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setFont(font)
        dlg.setDirectory(self.base_dir)
        if dlg.exec_() == QFileDialog.Accepted:
            dir_path = dlg.selectedFiles()[0]
            self.logger.info(f"User set reports folder: {dir_path}")
            self.base_dir = dir_path
            self.save_config()
            self.refresh_report_views()

    def refresh_report_views(self):
        """
        Refresh report browser/list views to reflect the new base_dir.
        """
        wet_plant_root = os.path.join(self.base_dir, "Wet Plant Reports")
        if hasattr(self, "hourly_report_view") and hasattr(self.hourly_report_view, "setRootIndex"):
            model = self.hourly_report_view.model()
            if model:
                path = os.path.join(wet_plant_root, "Hourly Reports")
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                model.setRootPath("")
                model.setRootPath(path)
                self.hourly_report_view.setRootIndex(model.index(path))
        if hasattr(self, "shift_report_view") and hasattr(self.shift_report_view, "setRootIndex"):
            model = self.shift_report_view.model()
            if model:
                path = os.path.join(wet_plant_root, "Shift Reports")
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                model.setRootPath("")
                model.setRootPath(path)
                self.shift_report_view.setRootIndex(model.index(path))
        self.logger.info("User refreshed report views")

    def setup_menu_bar(self):
        mb = self.menuBar()

        # --- Upload menu ---
        tpl = mb.addMenu("Upload")
        tpl.addAction("Hourly Template…",       self.upload_template)
        tpl.addAction("Shift Template…",        self.upload_shift_template)

        # Visual separator
        sep1 = QAction(self)
        sep1.setSeparator(True)
        mb.addAction(sep1)

        # --- Directories menu ---
        openm = mb.addMenu("Directories")
        openm.addAction("Hourly Reports",       self.open_hourly_reports)
        openm.addAction("Shift Reports",        self.open_shift_reports)

        # Visual separator
        sep2 = QAction(self)
        sep2.setSeparator(True)
        mb.addAction(sep2)

        # --- Reminders menu ---
        rem = mb.addMenu("Reminders")
        rem.addAction("Settings",               self.openReminderSettings)

        # Visual separator
        sep3 = QAction(self)
        sep3.setSeparator(True)
        mb.addAction(sep3)

        # --- Options menu ---
        options_menu = mb.addMenu("Options")
        options_menu.addAction("Preferences…", self.open_options_dialog)

        # Visual separator
        sep4 = QAction(self)
        sep4.setSeparator(True)
        mb.addAction(sep4)

        # --- Admin menu ---
        admin_menu = mb.addMenu("Admin")
        view_log_action = QAction("View Log", self)
        view_log_action.triggered.connect(self._show_log_with_password)
        admin_menu.addAction(view_log_action)

        # Visual separator
        sep5 = QAction(self)
        sep5.setSeparator(True)
        mb.addAction(sep5)

        # --- Support menu ---
        support_menu = mb.addMenu("&Support")
        support_action = QAction("Contact Support", self)
        support_action.triggered.connect(self.show_support_dialog)
        support_menu.addAction(support_action)

    def _set_admin_password(self):
        from PyQt5.QtWidgets import QInputDialog
        while True:
            pw, ok = QInputDialog.getText(self, "Set Admin Password", "Set a password for log access:", QLineEdit.Password)
            if not ok:
                QMessageBox.warning(self, "Required", "Admin password setup is required for log access.")
                continue
            pw2, ok2 = QInputDialog.getText(self, "Confirm Password", "Re-enter password:", QLineEdit.Password)
            if not ok2 or pw != pw2:
                QMessageBox.warning(self, "Mismatch", "Passwords do not match. Try again.")
                continue
            if len(pw) < 6:
                QMessageBox.warning(self, "Weak Password", "Password should be at least 6 characters.")
                continue
            break
        pw_hash = hashlib.sha256(pw.encode("utf-8")).hexdigest()
        self.config["admin_pw_hash"] = pw_hash
        self.save_config()
        self.logger.info("Admin password set/changed.")

    def _show_log_with_password(self):
        from PyQt5.QtWidgets import QInputDialog, QLineEdit, QTextEdit, QDialog, QVBoxLayout, QPushButton
        pw_hash = self.config.get("admin_pw_hash")
        if not pw_hash:
            self._set_admin_password()
            pw_hash = self.config.get("admin_pw_hash")
        password, ok = QInputDialog.getText(
            self, "Admin Access", "Enter password:", QLineEdit.Password
        )
        if not ok:
            return
        input_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if input_hash != pw_hash:
            msg = QMessageBox(self)
            msg.setWindowTitle("Access Denied")
            msg.setText("Incorrect password.")
            msg.setFont(QFont("Arial", self.font_size))
            msg.exec_()
            self.logger.warning("Failed log access attempt (wrong password)")
            return

        log_path = os.path.join(os.getcwd(), "wp_reports.log")
        if not os.path.exists(log_path):
            msg = QMessageBox(self)
            msg.setWindowTitle("Log Not Found")
            msg.setText("Log file not found.")
            msg.setFont(QFont("Arial", self.font_size))
            msg.exec_()
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(size - 5000, 0), 0)
                log_content = f.read()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Error")
            msg.setText(f"Could not read log file:\n{e}")
            msg.setFont(QFont("Arial", self.font_size))
            msg.exec_()
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("WP Reports Log")
        dlg.resize(800, 500)
        dlg.setFont(QFont("Arial", self.font_size))
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Arial", self.font_size))
        text.setPlainText(log_content)
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Arial", self.font_size))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec_()
        self.logger.info("Log file viewed via Admin menu")

    def open_options_dialog(self):
        dlg = OptionsDialog(
            self.font_size,
            self.window_width,
            self.window_height,
            self.dark_mode,
            self
        )
        if dlg.exec_() == QDialog.Accepted:
            font_size, win_w, win_h, dark_mode = dlg.get_settings()
            self.font_size = font_size
            self.window_width = win_w
            self.window_height = win_h
            self.dark_mode = dark_mode
            self.config["font_size"] = font_size
            self.config["window_width"] = win_w
            self.config["window_height"] = win_h
            self.config["dark_mode"] = dark_mode
            save_config(self.config)
            self.apply_font_size()
            self.apply_theme()
            self.resize(self.window_width, self.window_height)
            self.logger.info(f"User changed options: font_size={font_size}, window_width={win_w}, window_height={win_h}, dark_mode={dark_mode}")

    def apply_font_size(self):
        font = QFont("Arial", self.font_size)
        QApplication.instance().setFont(font)
        # Update browser font sizes if already created
        if hasattr(self, "hourly_report_view"):
            self.hourly_report_view.setFont(QFont("Arial", self.font_size))
        if hasattr(self, "shift_report_view"):
            self.shift_report_view.setFont(QFont("Arial", self.font_size))
        # Update all action buttons
        if hasattr(self, "buttons"):
            for btn in self.buttons:
                btn.setFont(QFont("Arial", self.font_size))

        self.logger.info(f"Font size applied: {self.font_size}")

    def on_theme_toggled(self, is_dark: bool):
        # Remove theme toggling logic entirely
        pass
        self.logger.info(f"Theme toggled: {'dark' if is_dark else 'light'}")

    def apply_theme(self):
        app = QApplication.instance()
        font = QFont("Arial", self.font_size)
        app.setFont(font)  # Ensure font size is set for all widgets in both modes
        if getattr(self, "dark_mode", False):
            # Apply dark palette
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(35, 35, 35))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            app.setStyle(QStyleFactory.create("Fusion"))
            app.setPalette(palette)
            self.menuBar().setStyleSheet(
                "QMenuBar { background: #353535; color: white; font-size: %dpt; } "
                "QMenuBar::item:selected { background: #2a82da; color: white; } "
                "QMenu { background: #353535; color: white; font-size: %dpt; } "
                "QMenu::item:selected { background: #2a82da; color: white; }"
                % (self.font_size, self.font_size)
            )
            if hasattr(self, "hourly_report_view"):
                self.hourly_report_view.setStyleSheet("background: #232323; color: white; font-size: %dpt;" % self.font_size)
            if hasattr(self, "shift_report_view"):
                self.shift_report_view.setStyleSheet("background: #232323; color: white; font-size: %dpt;" % self.font_size)
            self.logger.info("Theme applied (dark)")
        else:
            # Custom light palette for better contrast
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(245, 245, 245))  # slightly off-white
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(235, 235, 235))
            palette.setColor(QPalette.ToolTipBase, Qt.black)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(230, 230, 230))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(0, 102, 204))  # more blue
            palette.setColor(QPalette.Highlight, QColor(0, 120, 215))  # blue highlight
            palette.setColor(QPalette.HighlightedText, Qt.white)
            app.setStyle(QStyleFactory.create("Fusion"))
            app.setPalette(palette)
            self.menuBar().setStyleSheet(
                "QMenuBar { background: #f5f5f5; color: #222; border-bottom: 1px solid #bbb; font-size: %dpt; } "
                "QMenuBar::item:selected { background: #e0e0e0; color: #111; } "
                "QMenu { background: #f5f5f5; color: #222; font-size: %dpt; } "
                "QMenu::item:selected { background: #e0e0e0; color: #111; }"
                % (self.font_size, self.font_size)
            )
            if hasattr(self, "hourly_report_view"):
                self.hourly_report_view.setStyleSheet("background: #ffffff; color: #222; border: 1px solid #bbb; font-size: %dpt;" % self.font_size)
            if hasattr(self, "shift_report_view"):
                self.shift_report_view.setStyleSheet("background: #ffffff; color: #222; border: 1px solid #bbb; font-size: %dpt;" % self.font_size)
            self.logger.info("Theme applied (light)")

    def init_timers(self):
        # reminder sound
        self.sound = QSoundEffect(self)
        self.sound.setVolume(0.5)
        self.updateReminderSound()

        rt = QTimer(self)
        rt.timeout.connect(self.checkReminder)
        rt.start(60_000)

        dt = QTimer(self)
        dt.timeout.connect(self._rollover_date)
        dt.start(60_000)
        self.logger.info("Timers initialized")

    def updateReminderSound(self):
        if os.path.exists(self.reminder_audio):
            self.sound.setSource(QUrl.fromLocalFile(self.reminder_audio))
        else:
            self.sound.setSource(QUrl())
        self.logger.info(f"Reminder sound set: {self.reminder_audio}")

    def checkReminder(self):
        if not self.reminder_enabled:
            return
        now = datetime.datetime.now()
        if now.minute == (60 - self.reminder_minutes) and now.hour != self.last_reminder_hour:
            self.logger.info(f"Reminder triggered for hour {now.hour+1:02d}:00")
            self.sound.play()
            # bring main window to front
            self.showNormal()
            self.raise_()
            self.activateWindow()

            # custom top-level reminder dialog
            from PyQt5.QtWidgets import QMessageBox
            from PyQt5.QtCore    import Qt
            msg = QMessageBox(self)
            msg.setWindowTitle("Reminder")
            msg.setText(f"Reminder: Your report is due at {(now.hour+1)%24:02d}:00.")
            msg.setWindowModality(Qt.ApplicationModal)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()

            self.last_reminder_hour = now.hour

    def _rollover_date(self):
        today = QDate.currentDate()
        if hasattr(self, "hour_date")  and self.hour_date .date() != today:
            self.hour_date .setDate(today)
        if hasattr(self, "shift_date") and self.shift_date.date() != today:
            self.shift_date.setDate(today)
        self.logger.info("Date rollover checked")

    def open_hourly_reports(self):
        path = os.path.join(self.base_dir, "Wet Plant Reports", "Hourly Reports")
        if os.path.isdir(path):
            self.logger.info(f"User opened hourly reports folder: {path}")
            os.startfile(path)
        else:
            self.logger.warning(f"Hourly reports folder not found: {path}")
            QMessageBox.warning(self, "Not Found", f"No folder at:\n{path}")

    def open_shift_reports(self):
        path = os.path.join(self.base_dir, "Wet Plant Reports", "Shift Reports")
        if os.path.isdir(path):
            self.logger.info(f"User opened shift reports folder: {path}")
            os.startfile(path)
        else:
            self.logger.warning(f"Shift reports folder not found: {path}")
            QMessageBox.warning(self, "Not Found", f"No folder at:\n{path}")

    def upload_template(self):
        font = QFont("Arial", self.font_size)
        dlg = QFileDialog(self)
        dlg.setWindowTitle("Select Hourly Template")
        dlg.setNameFilters(["Excel Files (*.xlsx *.xls)"])
        dlg.setFont(font)
        if dlg.exec_() == QFileDialog.Accepted:
            fp = dlg.selectedFiles()[0]
            if not fp:
                return
            tag    = datetime.datetime.today().strftime("%d-%m-%y")
            folder = os.path.join(self.base_dir, "Wet Plant Reports", "Templates", "Hourly")
            os.makedirs(folder, exist_ok=True)
            _, ext = os.path.splitext(fp)
            dest   = os.path.join(folder, f"WPH_Template_{tag}{ext}")
            shutil.copy(fp, dest)
            self.template_path = dest
            self.config["template_path"] = dest
            save_config(self.config)
            self.logger.info(f"User uploaded hourly template: {dest}")
            QMessageBox.information(self, "Hourly Template Uploaded", dest)

    def upload_shift_template(self):
        font = QFont("Arial", self.font_size)
        dlg = QFileDialog(self)
        dlg.setWindowTitle("Select Shift Template")
        dlg.setNameFilters(["Excel Files (*.xlsx *.xls)"])
        dlg.setFont(font)
        if dlg.exec_() == QFileDialog.Accepted:
            fp = dlg.selectedFiles()[0]
            if not fp:
                return
            tag    = datetime.datetime.today().strftime("%d-%m-%y")
            folder = os.path.join(self.base_dir, "Wet Plant Reports", "Templates", "Shift")
            os.makedirs(folder, exist_ok=True)
            _, ext = os.path.splitext(fp)
            dest   = os.path.join(folder, f"WPS_Template_{tag}{ext}")
            shutil.copy(fp, dest)
            self.shift_template_path = dest
            self.config["shift_template_path"] = dest
            save_config(self.config)
            self.logger.info(f"User uploaded shift template: {dest}")
            QMessageBox.information(self, "Shift Template Uploaded", dest)


    def openReminderSettings(self):
        dlg = ReminderSettingsDialog(
            self.reminder_enabled,
            self.reminder_minutes,
            self.reminder_audio,
            self
        )
        dlg.setFont(QFont("Arial", self.font_size))
        if dlg.exec_() == QDialog.Accepted:
            self.reminder_enabled, self.reminder_minutes, self.reminder_audio = dlg.getSettings()
            save_config(self.config)
            self.updateReminderSound()
            self.logger.info(f"User updated reminder settings: enabled={self.reminder_enabled}, minutes={self.reminder_minutes}, audio={self.reminder_audio}")
            msg = QMessageBox(self)
            msg.setWindowTitle("Settings Saved")
            msg.setText("Reminder settings updated.")
            msg.setFont(QFont("Arial", self.font_size))
            msg.exec_()

    def run_setup_wizard(self):
        old_base_dir = self.base_dir
        self.logger.info("User started setup wizard")
        self.hide()
        wizard = SetupWizard(self.base_dir, self)
        wizard.setFont(QFont("Arial", self.font_size))
        result = wizard.exec_()
        self.show()
        if result == QDialog.Accepted:
            new_base_dir = wizard.get_base_dir()
            if new_base_dir and new_base_dir != old_base_dir:
                if os.path.isdir(old_base_dir):
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Move Existing Files?")
                    msg.setText("Do you want to move existing reports and templates to the new location?")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.setDefaultButton(QMessageBox.Yes)
                    msg.setFont(QFont("Arial", self.font_size))
                    reply = msg.exec_()
                    if reply == QMessageBox.Yes:
                        self.logger.info(f"User chose to move files from {old_base_dir} to {new_base_dir}")
                        self.move_reports_and_templates(old_base_dir, new_base_dir)
                self.logger.info(f"User set new base_dir: {new_base_dir}")
                self.base_dir = new_base_dir
                self.update_template_paths_after_move()
                self.save_config()
                self.refresh_report_views()

    def move_reports_and_templates(self, old_dir, new_dir):
        import shutil
        import os

        old_root = os.path.join(old_dir, "Wet Plant Reports")
        new_root = os.path.join(new_dir, "Wet Plant Reports")
        if os.path.exists(old_root):
            try:
                # Remove any pre-created folders in new_root to avoid nesting
                if os.path.exists(new_root):
                    shutil.rmtree(new_root)
                shutil.move(old_root, new_root)
                self.logger.info(f"Moved reports and templates from {old_root} to {new_root}")
            except Exception as e:
                # If move fails (e.g., files in use), copy all files and folders (including new ones)
                try:
                    if not os.path.exists(new_root):
                        os.makedirs(new_root, exist_ok=True)
                    for root, dirs, files in os.walk(old_root):
                        rel_path = os.path.relpath(root, old_root)
                        dest_dir = os.path.join(new_root, rel_path)
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir, exist_ok=True)
                        for file in files:
                            src_file = os.path.join(root, file)
                            dest_file = os.path.join(dest_dir, file)
                            if not os.path.exists(dest_file):
                                shutil.copy2(src_file, dest_file)
                    # Optionally, remove the old folder after copy
                    # shutil.rmtree(old_root)
                    self.logger.info(f"Copied reports and templates from {old_root} to {new_root}")
                except Exception as copy_e:
                    self.logger.error(f"Failed to move reports and templates: {e}")
                    self.logger.error(f"Failed to copy reports and templates: {copy_e}")
                    QMessageBox.warning(
                        self,
                        "Move Error",
                        f"Could not move or copy all files from {old_root} to {new_root}.\n\n"
                        f"Move error: {e}\nCopy error: {copy_e}\n\n"
                        "This may be because the application or another program is using files in this folder. "
                        "Please close all files and try again."
                    )

    def update_template_paths_after_move(self):
        """Update template paths in config if files exist in new location."""
        wet_plant_root = os.path.join(self.base_dir, "Wet Plant Reports")
        # Hourly template
        hourly_folder = os.path.join(wet_plant_root, "Templates", "Hourly")
        if os.path.isdir(hourly_folder):
            files = [f for f in os.listdir(hourly_folder) if f.lower().endswith(('.xlsx', '.xls'))]
            if files:
                # Use the most recently modified file
                files_full = [os.path.join(hourly_folder, f) for f in files]
                newest = max(files_full, key=os.path.getmtime)
                self.template_path = newest
                self.config["template_path"] = newest
        # Shift template
        shift_folder = os.path.join(wet_plant_root, "Templates", "Shift")
        if os.path.isdir(shift_folder):
            files = [f for f in os.listdir(shift_folder) if f.lower().endswith(('.xlsx', '.xls'))]
            if files:
                files_full = [os.path.join(shift_folder, f) for f in files]
                newest = max(files_full, key=os.path.getmtime)
                self.shift_template_path = newest
                self.config["shift_template_path"] = newest
        save_config(self.config)
        self.logger.info("Updated template paths after move")

    def _open_report_file(self, index):
        path = self.sender().model().filePath(index)
        if os.path.isfile(path):
            self.logger.info(f"User opened report file from browser: {path}")
            os.startfile(path)

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                self.config = json.load(f)
                self.base_dir = self.config.get("base_dir", os.getcwd())
                self.font_size = self.config.get("font_size", 16)
                self.window_width = self.config.get("window_width", 600)
                self.window_height = self.config.get("window_height", 600)
                self.dark_mode = self.config.get("dark_mode", False)
        except Exception:
            self.config = {}
            self.base_dir = os.getcwd()
            self.font_size = 16
            self.window_width = 600
            self.window_height = 600
            self.dark_mode = False
        # Use module-level logger if self.logger not set yet
        logger = getattr(self, "logger", logging.getLogger("WPReports"))
        logger.info("Configuration loaded")

    def save_config(self):
        self.config["base_dir"] = self.base_dir
        self.config["font_size"] = self.font_size
        self.config["window_width"] = self.window_width
        self.config["window_height"] = self.window_height
        self.config["dark_mode"] = getattr(self, "dark_mode", False)
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=2)
        logger = getattr(self, "logger", logging.getLogger("WPReports"))
        logger.info("Configuration saved")

    def init_help_menu(self):
        mb = self.menuBar()
        # Remove any existing Support menu to avoid duplicates
        for action in mb.actions():
            menu = action.menu()
            if menu and menu.title().replace("&", "").lower() == "support":
                mb.removeAction(action)
        # Add a "Support" menu with a regular action
        support_menu = mb.addMenu("&Support")
        support_action = QAction("Contact Support", self)
        support_action.triggered.connect(self.show_support_dialog)
        support_menu.addAction(support_action)
        self.logger.info("Help menu initialized")

    def show_support_dialog(self):
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Contact Support")
        msg.setText(
            "For questions, support, or reporting bugs contact:<br>"
            "<b>David Briley</b><br>"
            "<a href=\"mailto:dbriley@sourceenergyservices.com\">dbriley@sourceenergyservices.com</a><br>"
            "(905) 429-0959"
        )
        msg.setTextFormat(Qt.RichText)
        msg.setFont(QFont("Arial", self.font_size))
        msg.exec_()
        self.logger.info("User opened support dialog")

    def show_about_dialog(self):
        dlg = AboutDialog(font_size=self.font_size, parent=self)
        dlg.exec_()
        self.logger.info("User opened about dialog")

    

    def open_file_location(self, file_path: str):
        """
        Reveal the file in Explorer, highlighting it.
        If it's a folder, just open it.
        """
        try:
            # If it's a directory, open that folder directly
            if os.path.isdir(file_path):
                os.startfile(file_path)
                return

            # Otherwise, open the parent directory and highlight the file if possible
            if os.name == "nt":
                subprocess.Popen([
                    "explorer.exe",
                    f"/select,{file_path}"
                ])
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", "-R", file_path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(file_path)])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Could not open location for:\n{file_path}\n\n{e}"
            )


# ---- AboutDialog definition ----
class AboutDialog(QDialog):
    def __init__(self, font_size=12, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wet Plant Reports")
        self.setMinimumSize(500, 500)
        layout = QVBoxLayout(self)
        # Heading
        heading = QLabel("Wet Plant Reports")
        heading_font = QFont("Arial", max(font_size + 8, 18), QFont.Bold)
        heading.setFont(heading_font)
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)

        # Scrollable content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setText(f"""
            <div style="font-size:{font_size+2}px; font-family:Arial;">
            <h3 style="color:#2A82DA; margin-bottom:0;">Support</h3>            
            <hr>            
            <ul style="margin-left:0;">                
            </ul>
            <hr>
            <h4 style="color:#2A82DA;">Support</h4>
            <p>
                For questions or support, contact:<br>
                <b>David Briley</b><br>
                <a href="mailto:dbriley@sourceenergyservices.com">dbriley@sourceenergyservices.com</a><br>
                (905) 429-0959
            </p>
            <hr>            
            </div>
        """)
        label.setFont(QFont("Arial", font_size))
        content_layout.addWidget(label)
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.setFont(QFont("Arial", font_size))
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)
        layout.setAlignment(ok_btn, Qt.AlignCenter)

# ---- OptionsDialog definition ----
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QSpinBox, QDialogButtonBox, QHBoxLayout, QCheckBox

class OptionsDialog(QDialog):
    def __init__(self, font_size, window_width, window_height, dark_mode, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)

        # Font size
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font size:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 48)
        self.font_spin.setValue(font_size)
        font_row.addWidget(self.font_spin)
        layout.addLayout(font_row)

        # Window size
        win_row = QHBoxLayout()
        win_row.addWidget(QLabel("Window width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(400, 3840)
        self.width_spin.setValue(window_width)
        win_row.addWidget(self.width_spin)
        win_row.addWidget(QLabel("Window height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(300, 2160)
        self.height_spin.setValue(window_height)
        win_row.addWidget(self.height_spin)
        layout.addLayout(win_row)

        # Dark mode checkbox
        self.dark_mode_chk = QCheckBox("Enable dark mode")
        self.dark_mode_chk.setChecked(dark_mode)
        layout.addWidget(self.dark_mode_chk)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_settings(self):
        return (
            self.font_spin.value(),
            self.width_spin.value(),
            self.height_spin.value(),
            self.dark_mode_chk.isChecked()
        )

def main():
    app = QApplication(sys.argv)

    # Set the application-level icon
    icon_path = resource_path("raven.ico")
    app.setWindowIcon(QIcon(icon_path))

    app.setFont(QFont("Arial", 16))  # Change to Arial
    w = MainWindow()
    w.show()
    create_desktop_shortcut("Wet Plant Reports", icon_path)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("wp_reports.log"),
            logging.StreamHandler()
        ]
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



