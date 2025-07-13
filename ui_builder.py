import os
import logging  # <-- Add logging
import qtawesome as qta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QDateEdit, QComboBox, QPushButton, QTableView,
    QFileSystemModel, QMessageBox, QSizePolicy, QCalendarWidget, QToolButton, QMenu,
    QAbstractItemView
)
from PyQt5.QtCore import (
    QDate, QTime, Qt, QDir, QSize, QUrl
)
from PyQt5.QtGui import QFont, QPixmap, QDesktopServices
from PyQt5.QtWidgets import QDialog, QLabel, QSpacerItem, QApplication
from report_generator import create_hourly, create_shift

# Define APP_VERSION if not imported elsewhere
APP_VERSION = "1.0.0"


# Alternative: Use selection (highlighting) instead of checkboxes for file actions.
# Remove CheckableFileSystemModel and CheckBoxDelegate usage from make_tab:

def build_body_ui(main_win, parent_layout):
    # Ensure file_views and file_models are initialized
    if not hasattr(main_win, "file_views"):
        main_win.file_views = {}
    if not hasattr(main_win, "file_models"):
        main_win.file_models = {}

    # initialize button registry
    if not hasattr(main_win, "buttons"):
        main_win.buttons = []

    def make_tab(root_path, create_func, view_attr):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        ctrl = QHBoxLayout()
        ctrl.setAlignment(Qt.AlignLeft)
        date_edit = QDateEdit(calendarPopup=True, date=QDate.currentDate())
        date_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        ctrl.addWidget(date_edit)

        # ---- Flat calendar styling and custom icons ----
        cal = date_edit.calendarWidget()
        cal.setGridVisible(True)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        cal.setNavigationBarVisible(True)
        cal.setStyleSheet("""
            QCalendarWidget {
                background-color: #ffffff;
                border: 1px solid #dddddd;
                border-radius: 8px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #34495e;
                padding: 6px;
            }
            QCalendarWidget QAbstractItemView {
                selection-background-color: #2980b9;
                selection-color: #ffffff;
                font-size: 11pt;
            }
            QCalendarWidget QTableView {
                gridline-color: #ecf0f1;
            }
        """)
        prev_btn = cal.findChild(QToolButton, "qt_calendar_prevmonth")
        next_btn = cal.findChild(QToolButton, "qt_calendar_nextmonth")
        left_icon  = qta.icon('fa5s.chevron-left', color='white')
        right_icon = qta.icon('fa5s.chevron-right', color='white')
        if prev_btn is not None:
            prev_btn.setIcon(left_icon)
            prev_btn.setIconSize(QSize(20, 20))
            prev_btn.setMinimumSize(24, 24)
            prev_btn.setCursor(Qt.PointingHandCursor)
        if next_btn is not None:
            next_btn.setIcon(right_icon)
            next_btn.setIconSize(QSize(20, 20))
            next_btn.setMinimumSize(24, 24)
            next_btn.setCursor(Qt.PointingHandCursor)
        drop_btn = cal.findChild(QToolButton, "qt_calendar_monthbutton")
        if drop_btn:
            drop_btn.hide()
        # ---- end calendar styling ----

        if create_func == create_hourly:
            time_cb = QComboBox()
            time_cb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            for h in range(24):
                h12 = h % 12 or 12
                ampm = "AM" if h < 12 else "PM"
                time_cb.addItem(f"{h:02d}:00 ({h12}:00 {ampm})")
            time_cb.setCurrentIndex(QTime.currentTime().hour())
            ctrl.addWidget(time_cb)
            main_win.hour_date = date_edit
            main_win.hour_time = time_cb
        else:
            main_win.shift_date = date_edit
        btn = QPushButton(f"Create {'Hourly' if create_func==create_hourly else 'Shift'} Report")
        btn.setFont(QFont("Arial", main_win.font_size))
        btn.setMinimumHeight(date_edit.sizeHint().height())
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        def create_report_guarded():
            from PyQt5.QtWidgets import QMessageBox
            from datetime import datetime
            # If this is an hourly report (has time_cb), check hour and time constraints
            if create_func == create_hourly:
                selected_date = date_edit.date().toPyDate()
                selected_hour = time_cb.currentIndex()
                now = datetime.now()
                selected_dt = datetime.combine(selected_date, datetime.min.time()).replace(hour=selected_hour)
                # Disallow creating files more than 3 hours from now
                delta = selected_dt - now
                if abs(delta.total_seconds()) > 3 * 3600:
                    QMessageBox.warning(
                        None,
                        "Invalid Time",
                        "You cannot create an hourly report more than 3 hours from the current time."
                    )
                    return
            else:
                # Shift report: only date picker
                selected_date = date_edit.date().toPyDate()
                now = datetime.now().date()
                # Disallow creating files more than 2 days ahead
                if (selected_date - now).days > 2:
                    QMessageBox.warning(
                        None,
                        "Invalid Date",
                        "You cannot create a shift report more than 2 days ahead of today."
                    )
                    return
            create_func(main_win)

        btn.clicked.connect(create_report_guarded)
        ctrl.addWidget(btn)
        # register for dynamic font updates
        main_win.buttons.append(btn)

        refresh = QPushButton("Refresh")
        refresh.setFont(QFont("Arial", main_win.font_size))
        refresh.setMinimumHeight(date_edit.sizeHint().height())
        refresh.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        refresh.clicked.connect(main_win.refresh_report_views)
        ctrl.addWidget(refresh)
        # register refresh button
        main_win.buttons.append(refresh)

        layout.addLayout(ctrl)

        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignLeft)
        back_btn = QPushButton("Back")
        back_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        nav_layout.addWidget(back_btn)
        arrow_btn = QPushButton("↑")  # Use up arrow character for navigation
        arrow_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        nav_layout.addWidget(arrow_btn)
        layout.addLayout(nav_layout)

        view = QTableView()
        view.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        view.verticalHeader().setVisible(False)
        view.setDragEnabled(True)
        view.setAcceptDrops(False)
        view.setDragDropMode(QAbstractItemView.DragOnly)

        fs_model = QFileSystemModel(main_win)
        fs_model.setNameFilters(["*.xlsx"])
        fs_model.setNameFilterDisables(False)
        fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        fs_model.setRootPath(root_path)
        view.setModel(fs_model)
        view.setRootIndex(fs_model.index(root_path))

        # Hide Size (1) and Type (2) columns, keep Name (0) and Last Modified (3)
        view.hideColumn(1)
        view.hideColumn(2)

        from PyQt5.QtWidgets import QHeaderView
        view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Last Modified column

        # Navigation history for going back
        history = [fs_model.filePath(view.rootIndex())]

        def navigate_to(index):
            path = fs_model.filePath(index)
            if fs_model.isDir(index):
                view.setRootIndex(index)
                history.append(path)
                logging.info(f"User navigated to directory: {path}")

        def go_back():
            if len(history) > 1:
                history.pop()  # Remove current
                prev_path = history[-1]
                idx = fs_model.index(prev_path)
                view.setRootIndex(idx)
                logging.info(f"User navigated back to: {prev_path}")

        back_btn.clicked.connect(go_back)

        def on_double_click(idx):
            if fs_model.isDir(idx):
                navigate_to(idx)
            else:
                file_path = fs_model.filePath(idx)
                try:
                    import subprocess, sys
                    logging.info(f"User opened file from browser: {file_path}")
                    if sys.platform.startswith('darwin'):
                        subprocess.call(('open', file_path))
                    elif os.name == 'nt':
                        os.startfile(file_path)
                    elif os.name == 'posix':
                        subprocess.call(('xdg-open', file_path))
                except Exception as e:
                    QMessageBox.warning(view, "Open File Error", f"Could not open file:\n{file_path}\n\n{e}")
        view.doubleClicked.connect(on_double_click)

        # Right-click context menu to reveal file or folder in the OS file manager
        view.setContextMenuPolicy(Qt.CustomContextMenu)

        def on_context_menu(pos):
            # Map the click position to the index under the cursor
            idx = view.indexAt(pos)
            if idx.isValid():
                target = fs_model.filePath(idx)
            else:
                # empty area - use the current folder being viewed
                target = fs_model.rootPath() or root_path

            menu = QMenu(view)
            act = menu.addAction("Open File Location")
            act.triggered.connect(lambda _, p=target: main_win.open_file_location(p))
            menu.exec_(view.viewport().mapToGlobal(pos))

        view.customContextMenuRequested.connect(on_context_menu)

        # Fix: allow user to go up to parent directory
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Add a context menu or double-click on empty area to go up
        def go_up():
            current_idx = view.rootIndex()
            parent_idx = fs_model.parent(current_idx)
            if parent_idx.isValid():
                view.setRootIndex(parent_idx)
                history.append(fs_model.filePath(parent_idx))
                logging.info(f"User navigated up to: {fs_model.filePath(parent_idx)}")

        arrow_btn.clicked.connect(go_up)

        # Store the navigation history for this tab
        history = [root_path]

        def navigate_to(index):
            path = fs_model.filePath(index)
            if fs_model.isDir(index):
                view.setRootIndex(index)
                history.append(path)

        def go_back():
            if len(history) > 1:
                history.pop()  # Remove current
                prev_path = history[-1]
                idx = fs_model.index(prev_path)
                view.setRootIndex(idx)

        back_btn.clicked.connect(go_back)

        # Store references for later use (e.g., delete)
        if not hasattr(main_win, "file_views"):
            main_win.file_views = {}
        if not hasattr(main_win, "file_models"):
            main_win.file_models = {}
        main_win.file_views[view_attr] = view
        main_win.file_models[view_attr] = fs_model

        layout.addWidget(view)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setFont(QFont("Arial", main_win.font_size))
        delete_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        delete_btn.clicked.connect(lambda _, m=fs_model, r=root_path: _delete_selected(m, r, main_win))
        # register delete button
        main_win.buttons.append(delete_btn)

        layout.addWidget(delete_btn)

        setattr(main_win, view_attr, view)
        return tab

    tabs = QTabWidget()
    parent_layout.addWidget(tabs)

    wet_root = os.path.join(main_win.base_dir, "Wet Plant Reports")
    os.makedirs(wet_root, exist_ok=True)
    hourly_root = os.path.join(wet_root, "Hourly Reports")
    os.makedirs(hourly_root, exist_ok=True)
    shift_root = os.path.join(wet_root, "Shift Reports")
    os.makedirs(shift_root, exist_ok=True)

    tabs.addTab(make_tab(hourly_root, create_hourly, 'hourly_report_view'), "Hourly Reports")
    tabs.addTab(make_tab(shift_root,  create_shift,  'shift_report_view'),  "Shift Reports")


def _delete_selected(fs_model, root, main_win):
    # Get the correct view for the current tab
    if root.endswith("Hourly Reports"):
        view = main_win.hourly_report_view
    else:
        view = main_win.shift_report_view

    # Accept any selected index, not just selectedRows(0)
    selected_indexes = view.selectionModel().selectedIndexes()
    selected_rows = set(idx.row() for idx in selected_indexes)
    to_delete = []
    for row in selected_rows:
        idx = fs_model.index(row, 0, view.rootIndex())
        file_path = fs_model.filePath(idx)
        if idx.isValid() and not fs_model.isDir(idx) and os.path.isfile(file_path):
            to_delete.append(file_path)

    if not to_delete:
        QMessageBox.information(main_win, "Nothing Selected", "No files selected.")
        return

    # Use singular/plural prompt
    if len(to_delete) == 1:
        names = os.path.basename(to_delete[0])
        prompt = f"Delete this file?\n\n{names}"
    else:
        names = "\n".join(os.path.basename(p) for p in to_delete)
        prompt = f"Delete these files?\n\n{names}"

    if QMessageBox.question(
        main_win,
        "Confirm Deletion",
        prompt,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    ) != QMessageBox.Yes:
        return

    for p in to_delete:
        try:
            os.remove(p)
            logging.info(f"User deleted file: {p}")
        except Exception as e:
            logging.error(f"Failed to delete file {p}: {e}")
            QMessageBox.warning(main_win, "Error", f"Could not delete {p}:\n{e}")

    fs_model.setRootPath("")
    fs_model.setRootPath(root)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # Application logo
        logo_label = QLabel(self)
        logo_pixmap = QPixmap(":/images/logo.png")
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # Title
        title_label = QLabel("Wet Plant Reports", self)
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Version
        version_label = QLabel(f"Version {APP_VERSION}", self)
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        # Spacer
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Description
        desc_label = QLabel(
            "This application generates and manages Wet Plant reports.", self)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Support
        label = QLabel(self)
        font_size = QApplication.font().pointSize()
        label.setText(f"""
            <div style="font-size:{font_size+2}px; font-family:Arial;">
            <h3 style="color:#2A82DA; margin-bottom:0;">Support</h3>
            <hr>
            <p>
                For questions, support, or reporting bugs contact:<br>
                <b>David Briley</b><br>
                <a href="mailto:dbriley@sourceenergyservices.com">dbriley@sourceenergyservices.com</a><br>
                (905) 429-0959
            </p>
            <hr>
            </div>
        """)
        layout.addWidget(label)

        # Close button
        close_btn = QPushButton("Close", self)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        # Set stylesheet for title
        self.setStyleSheet("""
            #titleLabel {
                font-size: 18pt;
                font-weight: bold;
                color: #2A82DA;
            }
        """)
