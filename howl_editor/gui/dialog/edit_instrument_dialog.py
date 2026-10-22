# coding: utf-8

from dataclasses import dataclass

from PySide6.QtWidgets import QHBoxLayout, QSpinBox

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.voice.pitch_stepper import PitchStepper
from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize
from howl_editor.gui.widget.pitch_spin_box import PitchSpinBox
from howl_editor.ps1 import spu

_CEILING_WARNING = (
    "Above the SPU's 4.0× ceiling — the SPU plays it at 4.0× instead, so it comes out flat."
)


@dataclass(frozen=True)
class EditInstrumentResult:
    volume: int
    frequency: int
    adsr: int | None


class EditInstrumentDialog(StyledDialog):

    def __init__(
        self,
        parent,
        title: str,
        subject_label: str,
        initial_volume: int,
        initial_frequency: int,
        initial_adsr: int | None = None,
        pitch_stepper: PitchStepper | None = None,
    ):
        super().__init__(parent, title)
        self._stepper = pitch_stepper or PitchStepper()
        self.setMinimumWidth(WindowSize.EDIT_INSTRUMENT_WIDTH)
        self._build_ui(title, subject_label, initial_volume, initial_frequency, initial_adsr)

    def chosen(self) -> EditInstrumentResult:
        adsr: int | None = None

        if self._adsr_lo is not None and self._adsr_hi is not None:
            adsr = (self._adsr_hi.value() << 16) | self._adsr_lo.value()

        return EditInstrumentResult(
            volume=self._volume.value(),
            frequency=self._frequency.value(),
            adsr=adsr,
        )

    def _build_ui(
        self,
        title: str,
        subject_label: str,
        initial_volume: int,
        initial_frequency: int,
        initial_adsr: int | None,
    ) -> None:
        self.add_header(title, subject_label)

        form = self.form()
        self._body.addLayout(form)

        self._volume = QSpinBox()
        self._volume.setRange(0, cseq_fmt.MAX_VOLUME)
        self._volume.setValue(max(0, min(cseq_fmt.MAX_VOLUME, initial_volume)))
        self._volume.setSuffix(f" / {cseq_fmt.MAX_VOLUME}")
        form.addRow("Volume:", self._volume)

        self._frequency = PitchSpinBox(pitch_stepper=self._stepper)
        self._frequency.setValue(max(0, min(cseq_fmt.MAX_PITCH_REGISTER, initial_frequency)))
        self._frequency.valueChanged.connect(self._update_hz_label)
        form.addRow("Pitch register:", self._frequency)

        self._hz_label = self.hint()
        form.addRow("", self._hz_label)
        form.addRow("", self._build_octave_row())

        self._ceiling_label = self.callout()

        self._update_hz_label(self._frequency.value())

        self._adsr_lo: QSpinBox | None = None
        self._adsr_hi: QSpinBox | None = None

        if initial_adsr is not None:
            self._adsr_lo = self._make_hex_spinbox(initial_adsr & 0xFFFF)
            self._adsr_hi = self._make_hex_spinbox((initial_adsr >> 16) & 0xFFFF)
            form.addRow("Attack/Decay (ADSR1):", self._adsr_lo)
            form.addRow("Sustain/Release (ADSR2):", self._adsr_hi)

        self._body.addWidget(self._ceiling_label)
        self.add_footer(self.buttons("💾  Save"))

    def _build_octave_row(self) -> QHBoxLayout:
        """The spin box already steps octaves on Page Up/Down, but the common
        case deserves something visible."""
        row = QHBoxLayout()
        steps = (
            ("⬇️ Octave down", self._frequency.octave_down, "Halve", "down"),
            ("⬆️ Octave up", self._frequency.octave_up, "Double", "up"),
        )

        for label, slot, verb, direction in steps:
            row.addWidget(self.action_button(
                label, f"{verb} the pitch register — exactly one octave {direction}.",
                slot,
            ))

        row.addStretch()
        return row

    def _make_hex_spinbox(self, initial: int) -> QSpinBox:
        box = QSpinBox()
        box.setRange(0, cseq_fmt.MAX_ADSR_HALF)
        box.setValue(max(0, min(cseq_fmt.MAX_ADSR_HALF, initial)))
        box.setDisplayIntegerBase(16)
        box.setPrefix("0x")
        return box

    def _update_hz_label(self, raw: int) -> None:
        hz = int(raw / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)
        self._hz_label.setText(f"≈ {hz} Hz  ·  {raw / spu.FREQUENCY_UNIT:.2f}× speed")
        self.set_callout(
            self._ceiling_label,
            _CEILING_WARNING if self._stepper.exceeds_playable_ceiling(raw) else "",
        )
