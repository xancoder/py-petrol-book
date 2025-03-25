import datetime
import json
import logging
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import flet as ft

# Constants
APP_TITLE = "Petrol Book"
DEFAULT_PETROL_BOOK_FILENAME = "petrol_book.json"
DEFAULT_CALC_DISTANCE = 100
DEFAULT_THEME = ft.ThemeMode.SYSTEM

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class PetrolBookData:
    file_path: Optional[str] = None
    table_data: Dict[str, Any] = field(default_factory=dict)

    DEFAULT_TABLE_DATA = {
        "fuelingOperations": [],
        "meta": {"manufacturer": "", "model": ""},
        "units": {"costs": "\u20ac", "distance": "km", "liquid": "l"},
    }

    def read_file(self) -> Dict[str, Any]:
        """Read and parse petrol book file."""
        if not self.file_path:
            return self._initialize_default_data()

        pb_path = pathlib.Path(self.file_path)
        if not pb_path.exists():
            logger.warning(f"File {self.file_path} does not exist. Using default data.")
            return self._initialize_default_data()

        try:
            return self._load_data_from_file(pb_path)
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {self.file_path}: {str(e)}")
            return self._initialize_default_data()
        except Exception as e:
            logger.error(f"Unexpected error reading file {self.file_path}: {str(e)}")
            return self._initialize_default_data()

    def _initialize_default_data(self) -> Dict[str, Any]:
        """Initialize with default data and path if needed."""
        if not self.file_path:
            self.file_path = str(pathlib.Path.home() / DEFAULT_PETROL_BOOK_FILENAME)
        self.table_data = self.DEFAULT_TABLE_DATA.copy()
        return self.table_data

    def _load_data_from_file(self, file_path: pathlib.Path) -> Dict[str, Any]:
        """Load and parse data from the specified file."""
        with file_path.open(encoding="UTF-8") as source:
            self.table_data = json.load(source)
            logger.info(f"Successfully loaded data from {self.file_path}")
            return self.table_data

    def save_file(self) -> bool:
        """Save the current data to the file."""
        if not self.file_path:
            self.file_path = str(pathlib.Path.home() / DEFAULT_PETROL_BOOK_FILENAME)

        try:
            self._clean_temporary_fields()
            self._write_data_to_file()
            return True
        except Exception as e:
            logger.error(f"Failed to save data to {self.file_path}: {str(e)}")
            return False

    def _clean_temporary_fields(self) -> None:
        """Remove temporary fields before saving."""
        for operation in self.table_data.get("fuelingOperations", []):
            if "date_obj" in operation:
                del operation["date_obj"]

    def _write_data_to_file(self) -> None:
        """Write data to the file."""
        with open(self.file_path, "w", encoding="UTF-8") as file:
            json.dump(self.table_data, file, indent=2)
        logger.info(f"Successfully saved data to {self.file_path}")

    def add_fueling_operation(self, operation: Dict[str, Any]) -> bool:
        """Add a new fueling operation to the data."""
        try:
            if "fuelingOperations" not in self.table_data:
                self.table_data = self.DEFAULT_TABLE_DATA.copy()
            self.table_data["fuelingOperations"].append(operation)
            return True
        except Exception as e:
            logger.error(f"Failed to add fueling operation: {str(e)}")
            return False

    def sort_data(self) -> Dict[str, Any]:
        """Sort fueling operations by date in descending order."""
        if not self.table_data or "fuelingOperations" not in self.table_data:
            return self._initialize_default_data()

        operations = self.table_data.get("fuelingOperations", [])
        self._add_date_objects(operations)
        operations.sort(key=lambda x: x["date_obj"], reverse=True)
        return self.table_data

    def _add_date_objects(self, operations: List[Dict[str, Any]]) -> None:
        """Add date objects to operations for sorting purposes."""
        for row in operations:
            try:
                row["date_obj"] = datetime.datetime.strptime(row["date"], "%Y-%m-%d")
            except (ValueError, KeyError):
                # Set a default date if date is invalid or missing
                row["date_obj"] = datetime.datetime.min

    def get_units(self) -> Dict[str, str]:
        """Get the units from the table data."""
        return self.table_data.get("units", self.DEFAULT_TABLE_DATA["units"])

    def prepare_table_row_data(
        self, row: Dict[str, Any], start_mileage: float, calc_distance: int
    ) -> Dict[str, Any]:
        """Process a single data row for display with calculations."""
        result = {}
        units = self.get_units()

        # Format basic fields
        result = self._format_basic_fields(row, units, start_mileage)

        # Calculate derived values
        self._add_derived_calculations(result, row, calc_distance, units)
        return result

    def _format_basic_fields(
        self, row: Dict[str, Any], units: Dict[str, str], start_mileage: float
    ) -> Dict[str, Any]:
        """Format basic fields with appropriate units."""
        result = {}
        for field_name, value in row.items():
            if value == "" or value is None:
                result[field_name] = "-"
                continue

            if field_name == "costs":
                result[field_name] = f"{value:.2f} {units.get('costs', '')}"
            elif field_name == "liquid":
                result[field_name] = f"{value:.2f} {units.get('liquid', '')}"
            elif field_name == "distance":
                result[field_name] = f"{value:.1f} {units.get('distance', '')}"
            elif field_name == "mileage":
                result[field_name] = (
                    f"{int(value) - start_mileage} {units.get('distance', '')}"
                )
            else:
                result[field_name] = value
        return result

    def _add_derived_calculations(
        self,
        result: Dict[str, Any],
        row: Dict[str, Any],
        calc_distance: int,
        units: Dict[str, str],
    ) -> None:
        """Add derived calculations like cost per liter, etc."""
        if self._has_required_fields(row):
            try:
                # Cost per liter/volume
                result["cpl"] = (
                    f"{(row['costs'] / row['liquid']):.3f} {units.get('costs', '')} / "
                    f"{units.get('liquid', '')}"
                )
                # Cost per distance
                result["cpd"] = (
                    f"{(row['costs'] / row['distance'] * calc_distance):.2f} {units.get('costs', '')} / "
                    f"{calc_distance}{units.get('distance', '')}"
                )
                # Consumption rate (liquid per distance)
                result["lpd"] = (
                    f"{(row['liquid'] / row['distance'] * calc_distance):.2f} {units.get('liquid', '')} / "
                    f"{calc_distance}{units.get('distance', '')}"
                )
            except (ZeroDivisionError, TypeError):
                self._set_default_calculations(result)
        else:
            self._set_default_calculations(result)

    def _has_required_fields(self, row: Dict[str, Any]) -> bool:
        """Check if row has all required fields for calculations."""
        return all(key in row and row[key] for key in ["liquid", "costs", "distance"])

    def _set_default_calculations(self, result: Dict[str, Any]) -> None:
        """Set default values for calculations when data is missing."""
        result["cpl"] = "-"
        result["cpd"] = "-"
        result["lpd"] = "-"


class PetrolBookUI:
    """Manage UI components and interactions for petrol book."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.data_handler = PetrolBookData()
        # Initialize UI components
        self.setup_page()
        self.create_components()
        self.build_layout()

    # ===== Page Setup Methods =====
    def setup_page(self) -> None:
        """Configure page properties."""
        self.page.title = APP_TITLE
        self.page.theme_mode = DEFAULT_THEME
        self.page.adaptive = True
        self.page.on_app_lifecycle_state_change = self.handle_lifecycle_event

    def create_components(self) -> None:
        """Create UI components."""
        self._create_file_components()
        self._create_calculation_components()
        self._create_table_components()
        self._create_date_time_components()
        self._create_status_components()
        self._create_add_entry_components()

    def _create_file_components(self) -> None:
        """Create file-related UI components."""
        # File picker
        self.pick_files_dialog = ft.FilePicker(on_result=self.handle_file_pick_result)
        self.page.overlay.append(self.pick_files_dialog)

        # Text field for file path
        self.pb_file = ft.TextField(
            label="petrol book file",
            value="",
            read_only=True,
            expand=True,
            on_click=lambda _: self.pick_files_dialog.pick_files(allow_multiple=False),
        )

        # Button for file picker
        self.pb_file_picker = ft.IconButton(
            icon=ft.Icons.UPLOAD_FILE,
            on_click=lambda _: self.pick_files_dialog.pick_files(allow_multiple=False),
            tooltip="Select petrol book file",
        )

    def _create_calculation_components(self) -> None:
        """Create calculation-related UI components."""
        self.calc_distance_value = ft.TextField(
            label="per distance",
            value=DEFAULT_CALC_DISTANCE,
            expand=True,
            text_align=ft.TextAlign.RIGHT,
            on_change=lambda _: self.build_table(),
            hint_text="Enter distance for calculations",
        )

    def _create_table_components(self) -> None:
        """Create table-related UI components."""
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Station")),
                ft.DataColumn(ft.Text("Fuel Type")),
                ft.DataColumn(ft.Text("Cost")),
                ft.DataColumn(ft.Text("Volume")),
                ft.DataColumn(ft.Text("Distance")),
                ft.DataColumn(ft.Text("Mileage")),
                ft.DataColumn(ft.Text("Cost/Volume")),
                ft.DataColumn(ft.Text("Volume/Distance")),
                ft.DataColumn(ft.Text("Cost/Distance")),
            ],
            rows=[],
        )

    def _create_date_time_components(self) -> None:
        """Create date and time related UI components."""
        # Input fields for new entries
        self.input_date = ft.TextField(label="Date")
        self.input_time = ft.TextField(label="Time")

        # Date and time pickers
        self.date_picker = ft.DatePicker(
            on_change=self.handle_date_change, on_dismiss=self.handle_date_dismissal
        )
        self.time_picker = ft.TimePicker(on_change=self.handle_time_change)
        self.page.overlay.extend([self.date_picker, self.time_picker])

    def _create_status_components(self) -> None:
        """Create status-related UI components."""
        self.status_bar = ft.Text(value="Welcome to Petrol Book")

    def _create_add_entry_components(self) -> None:
        """Create components for adding new entries."""
        # Add Entry Button
        self.add_entry_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            text="Add Entry",
            on_click=self.show_add_entry_dialog,
            bgcolor=ft.Colors.BLUE,
        )

        # Date and time picker buttons
        date_picker_button = ft.IconButton(
            icon=ft.Icons.CALENDAR_TODAY,
            tooltip="Pick date",
            on_click=lambda _: self.page.open(self.date_picker),
        )

        time_picker_button = ft.IconButton(
            icon=ft.Icons.ACCESS_TIME,
            tooltip="Pick time",
            on_click=lambda _: self.page.open(self.time_picker),
        )

        # Add Entry Dialog
        self.add_entry_fields = {
            "date": ft.TextField(
                label="Date (YYYY-MM-DD)",
                value=datetime.date.today().strftime("%Y-%m-%d"),
                read_only=True,
                on_click=lambda _: self.page.open(self.date_picker),
                width=None,
                expand=True,
            ),
            "time": ft.TextField(
                label="Time (HH:MM)",
                value=datetime.datetime.now().strftime("%H:%M"),
                read_only=True,
                on_click=lambda _: self.page.open(self.time_picker),
                width=None,
                expand=True,
            ),
            "station": ft.TextField(
                label="Station", hint_text="Enter station name", width=None, expand=True
            ),
            "fuel_type": ft.Dropdown(
                label="Fuel Type",
                options=[
                    ft.dropdown.Option("Super E5"),
                    ft.dropdown.Option("Super E10"),
                    ft.dropdown.Option("Super Plus"),
                    ft.dropdown.Option("Diesel"),
                ],
                value="Super E5",
                hint_text="Select fuel type",
                width=None,
                expand=True,
            ),
            "costs": ft.TextField(
                label="Cost",
                hint_text="Enter cost",
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text=self.data_handler.DEFAULT_TABLE_DATA["units"]["costs"],
                width=None,
                expand=True,
            ),
            "liquid": ft.TextField(
                label="Volume",
                hint_text="Enter volume",
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text=self.data_handler.DEFAULT_TABLE_DATA["units"]["liquid"],
                width=None,
                expand=True,
            ),
            "distance": ft.TextField(
                label="Distance",
                hint_text="Enter distance traveled since last refill",
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text=self.data_handler.DEFAULT_TABLE_DATA["units"]["distance"],
                width=None,
                expand=True,
            ),
            "mileage": ft.TextField(
                label="Mileage",
                hint_text="Enter current odometer reading",
                keyboard_type=ft.KeyboardType.NUMBER,
                suffix_text=self.data_handler.DEFAULT_TABLE_DATA["units"]["distance"],
                width=None,
                expand=True,
            ),
            "units": self.data_handler.DEFAULT_TABLE_DATA["units"],
        }

        # Create the dialog content
        dialog_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Add New Fueling Operation", size=20, weight=ft.FontWeight.BOLD
                    ),
                    ft.Row(
                        [
                            self.add_entry_fields["date"],
                            date_picker_button,
                        ]
                    ),
                    ft.Row(
                        [
                            self.add_entry_fields["time"],
                            time_picker_button,
                        ]
                    ),
                    self.add_entry_fields["station"],
                    self.add_entry_fields["fuel_type"],
                    self.add_entry_fields["costs"],
                    self.add_entry_fields["liquid"],
                    self.add_entry_fields["distance"],
                    self.add_entry_fields["mileage"],
                    # self.add_entry_fields["notes"],
                    ft.Row(
                        [
                            ft.TextButton(
                                "Cancel", on_click=self.close_add_entry_dialog
                            ),
                            ft.FilledButton(
                                "Save",
                                on_click=self.save_new_entry,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                tight=True,
            ),
            expand=True,  # Makes the container expand to available width
            padding=10,
        )

        # Create the dialog
        self.add_entry_dialog = ft.AlertDialog(
            content=dialog_content,
            modal=True,
        )

        # Add dialog to page overlay
        self.page.overlay.append(self.add_entry_dialog)

    def build_layout(self) -> None:
        """Arrange UI components in the layout."""
        self.page.padding = 0
        self.page.add(
            ft.SafeArea(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row([self.pb_file, self.pb_file_picker]),
                            ft.Row([self.calc_distance_value]),
                            ft.Row(
                                [
                                    ft.Column(
                                        controls=[
                                            self.table,
                                        ],
                                        scroll=ft.ScrollMode.ALWAYS,
                                        expand=True,
                                    ),
                                ],
                                scroll=ft.ScrollMode.ALWAYS,
                                expand=True,
                            ),
                            self.status_bar,
                        ],
                        expand=True,
                        spacing=10,
                    )
                ),
                expand=True,
            )
        )
        self.page.floating_action_button = self.add_entry_button
        self.page.update()

    # ===== Event Handlers =====
    def handle_lifecycle_event(self, event) -> None:
        """Handle application lifecycle events."""
        if event.data == "detach":
            try:
                if self.page.platform == ft.PagePlatform.ANDROID:
                    self.page.window.destroy()
                    sys.exit(0)
            except Exception as e:
                logger.error(f"Error during app shutdown: {e}")

    def handle_file_pick_result(self, e: ft.FilePickerResultEvent) -> None:
        """Handle file picker result."""
        logger.info(f"pick files result: {e}")
        self.pb_file.value = None

        if e.files and e.files[0].path is not None:
            self.pb_file.value = e.files[0].path
            self.data_handler.file_path = e.files[0].path

            # Load and display data
            self.data_handler.read_file()
            self.data_handler.sort_data()
            self.build_table()

            # Update status
            self.status_bar.value = f"Loaded data from {e.files[0].path}"
        else:
            self.status_bar.value = "No file selected"

        self.pb_file.update()
        self.status_bar.update()

    def handle_date_change(self, e) -> None:
        """Handle date selection."""
        if hasattr(self, "add_entry_dialog") and self.add_entry_dialog.open:
            self.add_entry_fields["date"].value = e.date.strftime("%Y-%m-%d")
            self.add_entry_fields["date"].update()

    def handle_date_dismissal(self, e) -> None:
        """Handle date picker dismissal."""
        pass

    def handle_time_change(self, e) -> None:
        """Handle time selection."""
        if hasattr(self, "add_entry_dialog") and self.add_entry_dialog.open:
            self.add_entry_fields["time"].value = e.time.strftime("%H:%M")
            self.add_entry_fields["time"].update()

    def show_add_entry_dialog(self, e) -> None:
        """Show the dialog for adding a new entry."""
        # Pre-fill with today's date and current time
        self.add_entry_fields["date"].value = datetime.date.today().strftime("%Y-%m-%d")
        self.add_entry_fields["time"].value = datetime.datetime.now().strftime("%H:%M")

        # Clear other fields
        for field_name in ["station", "costs", "liquid", "distance", "mileage"]:
            self.add_entry_fields[field_name].value = ""

        # Reset fuel type dropdown
        self.add_entry_fields["fuel_type"].value = None

        # Update units from current data
        units = self.data_handler.get_units()
        self.add_entry_fields["costs"].suffix_text = units.get("costs", "€")
        self.add_entry_fields["liquid"].suffix_text = units.get("liquid", "l")
        self.add_entry_fields["distance"].suffix_text = units.get("distance", "km")
        self.add_entry_fields["mileage"].suffix_text = units.get("distance", "km")

        # Show dialog
        self.add_entry_dialog.open = True
        self.page.update()

    def close_add_entry_dialog(self, e) -> None:
        """Close the dialog without saving."""
        self.add_entry_dialog.open = False
        self.page.update()

    def save_new_entry(self, e) -> None:
        """Save the new entry to the data."""
        try:
            # Extract values from form fields
            new_entry = {
                "date": self.add_entry_fields["date"].value,
                "time": self.add_entry_fields["time"].value,
                "station": self.add_entry_fields["station"].value,
                "fuel_type": self.add_entry_fields["fuel_type"].value,
                # "notes": self.add_entry_fields["notes"].value,
            }

            # Convert numeric fields
            try:
                new_entry["costs"] = float(self.add_entry_fields["costs"].value)
            except (ValueError, TypeError):
                new_entry["costs"] = 0.0

            try:
                new_entry["liquid"] = float(self.add_entry_fields["liquid"].value)
            except (ValueError, TypeError):
                new_entry["liquid"] = 0.0

            try:
                new_entry["distance"] = float(self.add_entry_fields["distance"].value)
            except (ValueError, TypeError):
                new_entry["distance"] = 0.0

            try:
                new_entry["mileage"] = float(self.add_entry_fields["mileage"].value)
            except (ValueError, TypeError):
                new_entry["mileage"] = 0.0

            # Add entry to data
            if self.data_handler.add_fueling_operation(new_entry):
                # Save to file
                if self.data_handler.save_file():
                    self.update_status("New entry added and saved successfully")
                else:
                    self.update_status("New entry added but could not save to file")

                # Update the table
                self.data_handler.sort_data()
                self.build_table()
            else:
                self.update_status("Failed to add new entry")

            # Close dialog
            self.add_entry_dialog.open = False
            self.page.update()

        except Exception as e:
            logger.error(f"Error saving new entry: {str(e)}")
            self.update_status(f"Error adding entry: {str(e)}")

    def build_table(self) -> None:
        """Build and update the data table from the loaded data."""
        try:
            # Get calculation distance
            try:
                calc_distance = int(self.calc_distance_value.value)
            except (ValueError, TypeError):
                calc_distance = int(DEFAULT_CALC_DISTANCE)
                self.calc_distance_value.value = DEFAULT_CALC_DISTANCE

            # Generate table rows
            rows = self.generate_table_rows(calc_distance)

            # Update table
            self.table.rows = rows
            self.table.update()

            # Update status
            if rows:
                self.update_status(f"Showing {len(rows)} entries")
            else:
                self.update_status("No data available")

        except Exception as e:
            logger.error(f"Error building table: {str(e)}")
            self.update_status(f"Error building table: {str(e)}")

    def generate_table_rows(self, calc_distance: int) -> List[ft.DataRow]:
        """Generate table rows from the data."""
        rows = []
        operations = self.data_handler.table_data.get("fuelingOperations", [])

        if not operations:
            return rows

        # Find the start mileage (lowest mileage value)
        start_mileage = float("inf")
        for operation in operations:
            if "mileage" in operation and operation["mileage"] is not None:
                try:
                    mileage = float(operation["mileage"])
                    if mileage < start_mileage:
                        start_mileage = mileage
                except (ValueError, TypeError):
                    pass

        if start_mileage == float("inf"):
            start_mileage = 0

        # Process each row
        for operation in operations:
            processed = self.data_handler.prepare_table_row_data(
                operation, start_mileage, calc_distance
            )

            # Create DataRow
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(processed.get("date", "-"))),
                    ft.DataCell(ft.Text(processed.get("time", "-"))),
                    ft.DataCell(ft.Text(processed.get("station", "-"))),
                    ft.DataCell(ft.Text(processed.get("fuel_type", "-"))),
                    ft.DataCell(ft.Text(processed.get("costs", "-"))),
                    ft.DataCell(ft.Text(processed.get("liquid", "-"))),
                    ft.DataCell(ft.Text(processed.get("distance", "-"))),
                    ft.DataCell(ft.Text(processed.get("mileage", "-"))),
                    ft.DataCell(ft.Text(processed.get("cpl", "-"))),
                    ft.DataCell(ft.Text(processed.get("lpd", "-"))),
                    ft.DataCell(ft.Text(processed.get("cpd", "-"))),
                ]
            )
            rows.append(row)

        return rows

    def update_status(self, message: str) -> None:
        """Update the status bar with a message."""
        self.status_bar.value = message
        self.status_bar.update()


def main(page: ft.Page):
    """Initialize the application."""
    app = PetrolBookUI(page)


if __name__ == "__main__":
    ft.app(main)
