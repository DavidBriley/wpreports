# report_generator.py

import os
import shutil
import datetime
import logging  # <-- Add logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore    import QTime

def create_hourly(main_win):
    """
    Generate an hourly report in:
      base_dir/Wet Plant Reports/Hourly Reports/YYYY/Month/DD/
    using MM-DD-YYYY in the filename, with versioning if needed.
    """
    # 1) Build timestamp from the UI
    sel_date = main_win.hour_date.date().toPyDate()
    hour     = int(main_win.hour_time.currentText().split(":")[0])
    dt       = datetime.datetime.combine(sel_date, QTime(hour, 0).toPyTime())

    # 2) Format tags as MM-DD-YYYY and HH
    date_tag = dt.strftime("%m-%d-%Y")
    hour_tag = dt.strftime("%H")

    # 3) Build destination directory tree
    wet_plant_root = os.path.join(main_win.base_dir, "Wet Plant Reports")
    year_dir  = os.path.join(wet_plant_root, "Hourly Reports", dt.strftime("%Y"))
    month_dir = os.path.join(year_dir, dt.strftime("%B"))
    day_dir   = os.path.join(month_dir, f"{dt.day:02}")
    os.makedirs(day_dir, exist_ok=True)

    # 4) Construct the filename
    filename = f"WPH_Report_{date_tag}_{hour_tag}00.xlsx"
    dest_path = os.path.join(day_dir, filename)

    # 5) If it exists, prompt for a new version
    if os.path.exists(dest_path):
        answer = QMessageBox.question(
            main_win,
            "File Exists",
            f"{filename} already exists.\nCreate a new version?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if answer == QMessageBox.No:
            return

        base, ext = os.path.splitext(filename)
        v = 1
        while True:
            candidate = f"{base}_v{v}{ext}"
            candidate_path = os.path.join(day_dir, candidate)
            if not os.path.exists(candidate_path):
                dest_path = candidate_path
                break
            v += 1

    # 6) Copy from the template
    tpl = main_win.template_path
    if not (tpl and os.path.exists(tpl)):
        QMessageBox.warning(main_win, "No Template", "Please upload an hourly template first.")
        return
    shutil.copy(tpl, dest_path)
    logging.info(f"Hourly report created: {dest_path}")

    # 7) Ask to open
    if QMessageBox.question(
        main_win,
        "Open Report?",
        "Open the new hourly report now?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    ) == QMessageBox.Yes:
        logging.info(f"User opened hourly report: {dest_path}")
        os.startfile(dest_path)


def create_shift(main_win):
    """
    Generate a shift report in:
      base_dir/Wet Plant Reports/Shift Reports/YYYY/Month/
    using MM-DD-YYYY in the filename, with versioning if needed.
    """
    # 1) Build date from the UI
    sel_date = main_win.shift_date.date().toPyDate()
    date_tag = sel_date.strftime("%m-%d-%Y")

    # 2) Construct filename (no shift type)
    filename = f"WP Shift Report {date_tag}.xlsx"

    # 3) Build destination directory tree (no shift subfolder)
    wet_plant_root = os.path.join(main_win.base_dir, "Wet Plant Reports")
    year_dir  = os.path.join(wet_plant_root, "Shift Reports", sel_date.strftime("%Y"))
    month_dir = os.path.join(year_dir, sel_date.strftime("%B"))
    os.makedirs(month_dir, exist_ok=True)

    dest_path = os.path.join(month_dir, filename)

    # 4) Versioning if it exists
    if os.path.exists(dest_path):
        answer = QMessageBox.question(
            main_win,
            "File Exists",
            f"{filename} already exists.\nCreate a new version?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if answer == QMessageBox.No:
            return

        base, ext = os.path.splitext(filename)
        v = 1
        while True:
            candidate = f"{base}_v{v}{ext}"
            candidate_path = os.path.join(month_dir, candidate)
            if not os.path.exists(candidate_path):
                dest_path = candidate_path
                break
            v += 1

    # 5) Copy from the shift template
    tpl = main_win.shift_template_path
    if not (tpl and os.path.exists(tpl)):
        QMessageBox.warning(main_win, "No Template", "Please upload a shift template first.")
        return
    shutil.copy(tpl, dest_path)
    logging.info(f"Shift report created: {dest_path}")

    # 6) Ask to open
    if QMessageBox.question(
        main_win,
        "Open Report?",
        "Open the new shift report now?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    ) == QMessageBox.Yes:
        logging.info(f"User opened shift report: {dest_path}")
        os.startfile(dest_path)
