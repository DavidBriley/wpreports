import os
import datetime
import flet as ft
from report_generator import create_hourly, create_shift

BASE_DIR = os.getcwd()


def main(page: ft.Page):
    page.title = "Wet Plant Reports"
    page.window_width = 900
    page.window_height = 600

    # --- state ---
    hourly_items = []
    shift_items = []

    # --- helpers ---
    def list_reports(path):
        if not os.path.isdir(path):
            return []
        files = sorted(os.listdir(path))
        return [
            {"name": f, "path": os.path.join(path, f),
             "modified": datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(path, f))).strftime("%Y-%m-%d %H:%M")}
            for f in files if f.lower().endswith(".xlsx")
        ]

    def open_file(e):
        os.startfile(e.control.data)

    def refresh_hourly(e=None):
        date = dp_hourly.value or datetime.date.today()
        folder = os.path.join(BASE_DIR, "Wet Plant Reports", "Hourly Reports",
                              date.strftime("%Y"), date.strftime("%B"), f"{date.day:02}")
        items = list_reports(folder)
        table_hourly.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(it["name"], selectable=True), data=it["path"], on_double_tap=open_file),
                ft.DataCell(ft.Text(it["modified"]))
            ]) for it in items
        ]

    def refresh_shift(e=None):
        date = dp_shift.value or datetime.date.today()
        folder = os.path.join(BASE_DIR, "Wet Plant Reports", "Shift Reports",
                              date.strftime("%Y"), date.strftime("%B"))
        items = list_reports(folder)
        table_shift.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(it["name"], selectable=True), data=it["path"], on_double_tap=open_file),
                ft.DataCell(ft.Text(it["modified"]))
            ]) for it in items
        ]

    def create_hourly_report(e):
        d = dp_hourly.value or datetime.date.today()
        h = int(dd_hourly.value or 0)
        tpl = ""   # set your template path here
        create_hourly(d, h, tpl, BASE_DIR)
        refresh_hourly()

    def create_shift_report(e):
        d = dp_shift.value or datetime.date.today()
        tpl = ""   # set your template path here
        create_shift(d, tpl, BASE_DIR)
        refresh_shift()

    # --- controls ---
    dp_hourly = ft.DatePicker(value=datetime.date.today(), on_change=refresh_hourly)
    dd_hourly = ft.Dropdown(
        options=[ft.dropdown.Option(str(h)) for h in range(24)],
        value=str(datetime.datetime.now().hour),
        on_change=lambda e: None
    )
    btn_h_create = ft.ElevatedButton("Create", on_click=create_hourly_report)
    btn_h_refresh = ft.ElevatedButton("Refresh", on_click=refresh_hourly)
    table_hourly = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Name")), ft.DataColumn(ft.Text("Modified"))],
        rows=[]
    )

    dp_shift = ft.DatePicker(value=datetime.date.today(), on_change=refresh_shift)
    btn_s_create = ft.ElevatedButton("Create", on_click=create_shift_report)
    btn_s_refresh = ft.ElevatedButton("Refresh", on_click=refresh_shift)
    table_shift = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Name")), ft.DataColumn(ft.Text("Modified"))],
        rows=[]
    )

    # --- layout ---
    tab_h = ft.Column([
        ft.Row([dp_hourly, dd_hourly, btn_h_create, btn_h_refresh], spacing=10),
        table_hourly
    ], expand=True)

    tab_s = ft.Column([
        ft.Row([dp_shift, btn_s_create, btn_s_refresh], spacing=10),
        table_shift
    ], expand=True)

    tabs = ft.Tabs(tabs=[
        ft.Tab(text="Hourly Reports", content=tab_h),
        ft.Tab(text="Shift Reports", content=tab_s)
    ], expand=True)

    page.add(tabs)
    refresh_hourly()
    refresh_shift()


if __name__ == "__main__":
    ft.app(target=main)


# --- Helper functions for directory paths ---
def hourly_dir(base, date):
    return os.path.join(base, "Wet Plant Reports", "Hourly Reports",
                        date.strftime("%Y"), date.strftime("%B"), f"{date.day:02}")

def shift_dir(base, date):
    return os.path.join(base, "Wet Plant Reports", "Shift Reports",
                        date.strftime("%Y"), date.strftime("%B"))
