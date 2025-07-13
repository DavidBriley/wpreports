# WP Reports

## Setup
1. Install requirements: `pip install -r requirements.txt`
2. Run: `python main.py`

## Usage
- Create reports, manage templates, set reminders.
- Browse report folders and drag files directly into other applications (e.g. email).
- Right click a file or empty area to reveal it in your system's file browser.

## Packaging for computers without Python
Use [PyInstaller](https://pyinstaller.org/) to bundle the app and the Python
runtime into a standalone executable:

```bash
pip install pyinstaller
pyinstaller main.spec
```

The generated build can be found under `dist/`. Copy that folder to the target
machine and run the `main` executable – Python does not need to be installed.

## Troubleshooting
- Check `wp_reports.log` for errors.
