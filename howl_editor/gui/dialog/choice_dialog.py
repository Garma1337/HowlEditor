# coding: utf-8

from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox, QDialogButtonBox

from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize


@dataclass(frozen=True)
class ChoiceField:
    label: str
    options: list[str]
    current: int = 0


class ChoiceDialog(StyledDialog):
    """Pick one entry from each of a few lists — a source bank, a sequence, a
    bank and song to check together. Asking for related picks on one screen
    saves a chain of single-question popups."""

    def __init__(
        self, parent, title: str, subtitle: str, fields: list[ChoiceField],
        primary_text: str = "✅  OK",
    ):
        super().__init__(parent, title)
        self.setMinimumWidth(WindowSize.CHOICE_WIDTH)
        self._combos: list[QComboBox] = []

        self.add_header(title, subtitle)
        form = self.form()
        self._body.addLayout(form)

        for field in fields:
            combo = QComboBox()
            combo.addItems(field.options)
            combo.setCurrentIndex(field.current)
            form.addRow(field.label, combo)
            self._combos.append(combo)

        buttons = self.buttons(primary_text)

        # An empty field would report -1, which silently indexes the last
        # entry of the caller's list, so there is nothing to confirm.
        if any(not field.options for field in fields):
            for button in buttons.buttons():
                if buttons.buttonRole(button) == QDialogButtonBox.AcceptRole:
                    button.setEnabled(False)

        self.add_footer(buttons)

    def chosen(self) -> list[int]:
        """The picked position in each field's options, in field order."""
        return [combo.currentIndex() for combo in self._combos]
