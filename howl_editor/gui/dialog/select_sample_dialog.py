# coding: utf-8

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QLineEdit, QListWidgetItem,
)

from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize
from howl_editor.gui.sample_choice import SampleChoice

__all__ = ["SampleChoice", "SelectSampleDialog"]


class SelectSampleDialog(StyledDialog):

    FREE_MARK = "  ·  🆓 free"

    def __init__(
        self,
        parent,
        title: str,
        prompt: str,
        choices: list[SampleChoice],
        current_spu_index: int | None = None,
        on_preview: Callable[[int], None] | None = None,
        pitch_option: str | None = None,
    ):
        super().__init__(parent, title)
        self.resize(WindowSize.SELECT_SAMPLE_WIDTH, WindowSize.SELECT_SAMPLE_HEIGHT)
        self._choices = choices
        self._current = current_spu_index
        self._on_preview = on_preview
        self._pitch_option = None
        self._build_ui(title, prompt, pitch_option)

    def chosen_spu_index(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None

        return item.data(Qt.UserRole)

    def adopt_pitch(self) -> bool:
        """Whether the caller should move the descriptor onto the chosen
        sample's pitch."""
        return self._pitch_option is not None and self._pitch_option.isChecked()

    def _build_ui(self, title: str, prompt: str, pitch_option: str | None) -> None:
        self.add_header(title, prompt)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter…")
        self._filter.setClearButtonEnabled(True)
        self._filter.textChanged.connect(self._apply_filter)
        self._body.addWidget(self._filter)

        self._list = self.pick_list()
        self._body.addWidget(self._list, stretch=1)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        self._populate()

        if pitch_option is not None:
            self._pitch_option = QCheckBox(pitch_option)
            self._pitch_option.setChecked(True)
            self._body.addWidget(self._pitch_option)

        leading = []

        if self._on_preview is not None:
            self._preview_button = self.action_button(
                "▶️  Preview",
                "Play the highlighted sample so you can hear it before picking.",
                self._preview_selected,
            )
            leading.append(self._preview_button)

        self.add_footer(self.buttons("✅  Select"), *leading)

    def _preview_selected(self) -> None:
        spu_index = self.chosen_spu_index()
        if spu_index is not None and self._on_preview is not None:
            self._on_preview(spu_index)

    def _populate(self) -> None:
        self._list.clear()

        selected = False

        for choice in self._choices:
            item = QListWidgetItem(self._label(choice))
            item.setData(Qt.UserRole, choice.spu_index)

            if choice.tooltip:
                item.setToolTip(choice.tooltip)

            if not choice.enabled:
                item.setFlags(item.flags() & ~(Qt.ItemIsEnabled | Qt.ItemIsSelectable))

            self._list.addItem(item)

            if not selected and choice.enabled and choice.spu_index == self._current:
                self._list.setCurrentItem(item)
                self._list.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                selected = True

    def _label(self, choice: SampleChoice) -> str:
        return choice.display + self.FREE_MARK if choice.free else choice.display

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setHidden(needle != "" and needle not in item.text().lower())
