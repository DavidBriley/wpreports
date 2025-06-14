# utils.py

import sys
import os
import logging
from typing import Optional

try:
    import win32com.client
except ImportError:
    win32com = None  # For cross-platform support

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("wp_reports.log"),
        logging.StreamHandler()
    ]
)

def resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource file, whether in
    development or in a PyInstaller bundle.

    Args:
        relative_path (str): Relative path to the resource.

    Returns:
        str: Absolute path to the resource.
    """
    try:
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        abs_path = os.path.join(base_path, relative_path)
        logging.debug(f"Resolved resource path: {abs_path}")
        return abs_path
    except Exception as e:
        logging.error(f"Error resolving resource path: {e}")
        raise

def create_desktop_shortcut(name: str, icon_path: str) -> None:
    """
    Create a .lnk on the current user's Desktop that points
    at the running Python executable, with the given icon.

    Args:
        name (str): Shortcut name.
        icon_path (str): Path to the icon file.
    """
    if os.name != "nt" or win32com is None:
        logging.warning("Shortcut creation is only supported on Windows with pywin32 installed.")
        print("Shortcut creation is only supported on Windows with pywin32 installed.")
        return

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = shell.SpecialFolders("Desktop")
        link_path = os.path.join(desktop, f"{name}.lnk")

        shortcut = shell.CreateShortCut(link_path)
        shortcut.Targetpath       = sys.executable
        shortcut.WorkingDirectory = os.getcwd()
        shortcut.IconLocation     = icon_path
        shortcut.save()
        logging.info(f"Shortcut created at {link_path}")
    except Exception as e:
        logging.error(f"Failed to create desktop shortcut: {e}")
        print(f"Could not create shortcut: {e}")


