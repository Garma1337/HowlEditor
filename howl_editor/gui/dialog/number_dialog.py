# coding: utf-8

from PySide6.QtWidgets import QSpinBox

from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize


class NumberDialog(StyledDialog):
    """Ask for one whole number within a range."""

    def __init__(
        self, parent, title: str, subtitle: str, label: str,
        value: int, minimum: int, maximum: int, suffix: str = "",
        primary_text: str = "✅  OK",
    ):
        super().__init__(parent, title)
        self.setMinimumWidth(WindowSize.CHOICE_WIDTH)

        self.add_header(title, subtitle)
        form = self.form()
        self._body.addLayout(form)

        self._spin = QSpinBox()
        self._spin.setRange(minimum, maximum)
        self._spin.setValue(value)
        self._spin.setSuffix(suffix)
        form.addRow(label, self._spin)

        self.add_footer(self.buttons(primary_text))

    def value(self) -> int:
        return self._spin.value()
