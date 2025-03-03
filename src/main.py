import datetime
import json
import logging
import pathlib
import sys

import flet as ft

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler("application.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def main(page: ft.Page):
    def handle_lifecycle_event(event):
        if event.data == 'detach':
            try:
                if page.platform == ft.PagePlatform.ANDROID:
                    page.window.destroy()
                    sys.exit(0)
            except Exception as e:
                logger.error(f"Error during app shutdown: {e}")

    page.on_app_lifecycle_state_change = handle_lifecycle_event
    page.title = "Petrol Book"
    page.theme_mode = ft.ThemeMode.DARK
    page.adaptive = True

    def read_petrol_book(petrol_book_file: str) -> dict:
        logger.info(f"read petrol book file: {petrol_book_file}")
        table_data_default = {
            'fuelingOperations': [],
            'meta': {
                'manufacturer': '',
                'model': ''
            },
            'units': {
                'costs': '\u20ac',
                'distance': 'km',
                'liquid': 'l'
            }
        }

        if petrol_book_file == '':
            status_bar_start.value = "please check your path or new file will created"
            status_bar_start.update()
            return table_data_default

        pb_path = pathlib.Path(petrol_book_file)
        if pb_path.is_dir():
            status_bar_start.value = "please selected a petrol book file"
            status_bar_start.update()
            return table_data_default

        try:
            with pb_path.open(encoding='UTF-8') as source:
                return json.load(source)
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {petrol_book_file}: {str(e)}")
            status_bar_start.value = "Invalid JSON format in the petrol book file"
            status_bar_start.update()
            return table_data_default

    def sort_table_data(td: dict):
        for row in td['fuelingOperations']:
            row["date_obj"] = datetime.datetime.strptime(row["date"], "%Y-%m-%d")
        td['fuelingOperations'].sort(key=lambda x: x["date_obj"], reverse=True)
        return td

    def build_table(td: dict):
        if len(td['fuelingOperations']) == 0:
            status_bar_start.value = "petrol book file is empty"
            return

        status_bar_start.value = "building petrol book table"
        start_ma = td['fuelingOperations'][-1]['mileage'] - td['fuelingOperations'][-1]['distance']

        btd = []
        for row in td['fuelingOperations']:
            tmp = {}
            for row_value in row:
                if row[row_value] == '' or row[row_value] is None:
                    tmp[row_value] = f"-"
                    continue

                if row_value == 'costs':
                    tmp[row_value] = f"{row[row_value]:.2f} {row['units']['costs']}"
                elif row_value == 'liquid':
                    tmp[row_value] = f"{row[row_value]:.2f} {row['units']['liquid']}"
                elif row_value == 'distance':
                    tmp[row_value] = f"{row[row_value]:.1f} {row['units']['distance']}"
                elif row_value == 'mileage':
                    tmp[row_value] = f"{int(row[row_value]) - start_ma} {row['units']['distance']}"
                else:
                    tmp[row_value] = row[row_value]

            if row['liquid'] is None:
                tmp["cpl"] = f"-"
                tmp["cpd"] = f"-"
                tmp["lpd"] = f"-"
            else:
                cplv = round(float(row['costs']) / float(row['liquid']), 3)
                cpdv = round((float(row['costs']) / float(row['distance']) * int(calc_distance_value.value)), 2)
                lpdv = round((float(row['liquid']) / float(row['distance']) * int(calc_distance_value.value)), 2)
                tmp["cpl"] = f"{cplv:.3f} {row['units']['costs']} / {row['units']['liquid']}"
                tmp[
                    "cpd"] = f"{cpdv:.2f} {row['units']['costs']} / {int(calc_distance_value.value)}{row['units']['distance']}"
                tmp[
                    "lpd"] = f"{lpdv:.2f} {row['units']['liquid']} / {int(calc_distance_value.value)}{row['units']['distance']}"

            btd.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tmp["date"])),
                        ft.DataCell(ft.Text(tmp["time"])),
                        ft.DataCell(ft.Text(tmp["petrolStation"])),
                        ft.DataCell(ft.Text(tmp["petrolType"])),
                        ft.DataCell(ft.Text(tmp["costs"])),
                        ft.DataCell(ft.Text(tmp["liquid"])),
                        ft.DataCell(ft.Text(tmp["distance"])),
                        ft.DataCell(ft.Text(tmp["mileage"])),
                        ft.DataCell(ft.Text(tmp["cpl"])),
                        ft.DataCell(ft.Text(tmp["lpd"])),
                        ft.DataCell(ft.Text(tmp["cpd"])),
                    ],
                )
            )

        table.rows = btd
        table.update()

        status_bar_start.value = "petrol book file loaded successfully"
        status_bar_start.update()

    def pick_files_result(e: ft.FilePickerResultEvent):
        logger.info(f"pick files result: {e}")
        if e.files:
            pb_file.value = e.files[0].path
        else:
            pb_file.value = "Cancelled!"
        pb_file.update()

        table_data = read_petrol_book(pb_file.value)
        table_data_sorted = sort_table_data(table_data)
        build_table(table_data_sorted)

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    pb_file = ft.TextField(
        label="petrol book file",
        disabled=True,
        expand=True,
    )
    page.overlay.append(pick_files_dialog)
    pb_file_picker = ft.IconButton(
        icon=ft.Icons.UPLOAD_FILE,
        on_click=lambda _: pick_files_dialog.pick_files(
            allow_multiple=False
        ),
    )

    calc_distance_value = ft.TextField(
        label="distance calculation value",
        value="100",
        expand=True,
        on_change=lambda _: build_table(sort_table_data(read_petrol_book(pb_file.value))),
    )

    table = ft.DataTable(
        horizontal_margin=10,
        expand=True,
        border=ft.core.border.all(1),
        columns=[
            ft.DataColumn(ft.Text("Date")),
            ft.DataColumn(ft.Text("Time")),
            ft.DataColumn(ft.Text("PetrolStation")),
            ft.DataColumn(ft.Text("PetrolType")),
            ft.DataColumn(ft.Text("Costs"), numeric=True),
            ft.DataColumn(ft.Text("Liquid"), numeric=True),
            ft.DataColumn(ft.Text("Distance"), numeric=True),
            ft.DataColumn(ft.Text("Mileage"), numeric=True),
            ft.DataColumn(ft.Text("Costs / Liquid")),
            ft.DataColumn(ft.Text(f"Liquid / Distance")),
            ft.DataColumn(ft.Text(f"Costs / Distance")),
        ]
    )

    status_bar_start = ft.Text(value="please select a petrol book file")
    status_bar_center = ft.Text(value="")
    status_bar_end = ft.Text(value="v1.0.0 by xancoder")

    page.add(
        ft.SafeArea(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                pb_file_picker,
                                pb_file,
                            ],
                        ),
                        ft.Row(
                            controls=[
                                calc_distance_value,
                            ],
                        ),
                        ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[table],
                                    scroll=ft.ScrollMode.ALWAYS,
                                    expand=True,
                                ),
                            ],
                            scroll=ft.ScrollMode.ALWAYS,
                            expand=True,
                        ),
                        ft.Row(
                            controls=[
                                status_bar_start,
                                status_bar_center,
                                status_bar_end,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    alignment=ft.alignment.center,
                )
            ),
            expand=True,
        )
    )


ft.app(main)
