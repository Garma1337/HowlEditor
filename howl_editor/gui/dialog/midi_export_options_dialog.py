# coding: utf-8

from PySide6.QtWidgets import QCheckBox

from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize
from howl_editor.midi.export_options import MidiExportOptions


class MidiExportOptionsDialog(StyledDialog):

    def __init__(self, parent, defaults: MidiExportOptions = MidiExportOptions()):
        super().__init__(parent, "MIDI export options")
        self.setMinimumWidth(WindowSize.MIDI_EXPORT_WIDTH)
        self._build_ui(defaults)

    def chosen(self) -> MidiExportOptions:
        return MidiExportOptions(
            include_volume_events=self._include_volume.isChecked(),
            apply_instrument_volume=self._apply_inst.isChecked(),
        )

    def _build_ui(self, defaults: MidiExportOptions) -> None:
        self.add_header("MIDI export options", "Adjust how this MIDI is written.")

        self._include_volume = QCheckBox("Include in-song volume changes (CC#7)")
        self._include_volume.setChecked(defaults.include_volume_events)
        self._body.addLayout(self.option_with_hint(
            self._include_volume,
            "When off, mid-song volume changes are dropped so the DAW hears raw note velocities.",
        ))

        self._apply_inst = QCheckBox("Apply each track's instrument volume at start")
        self._apply_inst.setChecked(defaults.apply_instrument_volume)
        self._body.addLayout(self.option_with_hint(
            self._apply_inst,
            "When on, each track gets a CC#7 volume set from the instrument it's bound to.",
        ))

        self.add_footer(self.buttons("📤  Export…"))
