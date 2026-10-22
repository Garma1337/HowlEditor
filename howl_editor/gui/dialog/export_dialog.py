# coding: utf-8

from PySide6.QtWidgets import QButtonGroup, QRadioButton

from howl_editor.file_format_registry import FileFormat
from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize


class ExportDialog(StyledDialog):

    def __init__(self, parent, target_label: str, options: list[FileFormat]):
        super().__init__(parent, f"Export {target_label}")
        self.setMinimumWidth(WindowSize.EXPORT_WIDTH)
        self._options = options
        self._group = QButtonGroup(self)
        self._radios: list[QRadioButton] = []
        self._build_ui(target_label)

    def chosen_format(self) -> FileFormat | None:
        for i, radio in enumerate(self._radios):
            if radio.isChecked():
                return self._options[i]

        return None

    def _build_ui(self, target_label: str) -> None:
        self.add_header(f"Export {target_label}", "Choose the format to save it as.")

        for i, fmt in enumerate(self._options):
            radio = QRadioButton(f"{fmt.display_name}  ({fmt.extension})")

            if i == 0:
                radio.setChecked(True)

            self._group.addButton(radio, i)
            self._radios.append(radio)
            self._body.addWidget(radio)

        self.add_footer(self.buttons("📤  Export…"))
