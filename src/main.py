import json
import logging
import os
import pathlib

import flet as ft

logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("application.log", encoding="utf-8"),  # Log to a file
        logging.StreamHandler(),  # Log to the console
    ],
)

logger = logging.getLogger(__name__)


def main(page: ft.Page):
    calc_distance = 100

    page.title = "Petrol Book"
    page.theme_mode = ft.ThemeMode.DARK
    page.adaptive = True

    def event(e):
        if e.data == 'detach' and page.platform == ft.PagePlatform.ANDROID:
            os._exit(1)

    page.on_app_lifecycle_state_change = event

    def read_petrol_book(pb_file: str) -> dict:
        logger.info(f"read petrol book file: {pb_file}")

        if pb_file == '':
            status_bar_start.value('please enter petrol-book file')

        pb_path = pathlib.Path(pb_file)
        with pb_path.open(encoding='UTF-8') as source:
            return json.load(source)

    def build_table(pb_file: str):
        logger.info(f"build table from petrol book file: {pb_file}")
        pb_path = pathlib.Path(pb_file)
        if pb_path.is_dir():
            status_bar_start.value = "please check your petrol book file"

        if not pb_path.exists():
            status_bar_start.value = "please check your path or new file will created"
            content = {
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

        else:
            content = read_petrol_book(pb_file)
            logger.info(f"content: {content}")

            data = []
            start_ma = content['fuelingOperations'][0]['mileage'] - content['fuelingOperations'][0]['distance']
            for i in content['fuelingOperations']:
                cplv = float(i['costs']) / float(i['liquid'])
                cpdv = float(i['costs']) / float(i['distance'])
                lpdv = float(i['liquid']) / float(i['distance'])
                cpl = f"{round(cplv, 3)} {i['units']['costs']} / {i['units']['liquid']}"
                cpd = f"{round(cpdv * calc_distance, 2)} {i['units']['costs']} / {calc_distance}{i['units']['distance']}"
                lpd = f"{round(lpdv * calc_distance, 2)} {i['units']['liquid']} / {calc_distance}{i['units']['distance']}"
                data.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(i['date'])),
                            ft.DataCell(ft.Text(i['time'])),
                            ft.DataCell(ft.Text(i['petrolStation'])),
                            ft.DataCell(ft.Text(i['petrolType'])),
                            ft.DataCell(ft.Text(f"{i['costs']} {i['units']['costs']}")),
                            ft.DataCell(ft.Text(f"{i['liquid']} {i['units']['liquid']}")),
                            ft.DataCell(ft.Text(f"{i['distance']} {i['units']['distance']}")),
                            ft.DataCell(ft.Text(f"{int(i['mileage']) - start_ma} {i['units']['distance']}")),
                            ft.DataCell(ft.Text(f"{cpl}")),
                            ft.DataCell(ft.Text(f"{lpd}")),
                            ft.DataCell(ft.Text(f"{cpd}"))
                        ],
                    )
                )
            table.rows = data
            table.update()

    def pick_files_result(e: ft.FilePickerResultEvent):
        logger.info(f"pick files result: {e}")
        pb_file.value = (
            ", ".join(map(lambda f: f.path, e.files)) if e.files else "Cancelled!"
        )
        pb_file.update()
        build_table(pb_file.value)

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    pb_file = ft.TextField(
        label="petrol book file",
        border=ft.InputBorder.NONE,
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

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Date")),
            ft.DataColumn(ft.Text("Time")),
            ft.DataColumn(ft.Text("PetrolStation")),
            ft.DataColumn(ft.Text("PetrolType")),
            ft.DataColumn(ft.Text("Costs"), numeric=True),
            ft.DataColumn(ft.Text("Liquid"), numeric=True),
            ft.DataColumn(ft.Text("Distance"), numeric=True),
            ft.DataColumn(ft.Text("Mileage"), numeric=True),
            ft.DataColumn(ft.Text("Costs / Liquid"), numeric=True),
            ft.DataColumn(ft.Text(f"Liquid / {calc_distance}"), numeric=True),
            ft.DataColumn(ft.Text(f"Costs / {calc_distance}"), numeric=True),
        ],
        sort_column_index=0,
        sort_ascending=False,
        expand=True,
    )

    status_bar_start = ft.Text(value="please upload petrol book file")
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
                        ft.Column(
                            controls=[
                                table,
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.ALWAYS,
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
