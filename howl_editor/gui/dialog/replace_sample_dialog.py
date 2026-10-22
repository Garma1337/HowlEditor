# coding: utf-8

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QRadioButton, QVBoxLayout

from howl_editor.ctr.analysis.sample_replacement_planner import SampleReplacementPlan
from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize
from howl_editor.saphi.constants import SAPHI_BANK_MAX_SIZE


@dataclass(frozen=True)
class ReplaceSampleChoice:
    update_shared_banks: bool
    retune_songs: bool = False


class ReplaceSampleDialog(StyledDialog):
    """One prompt for a sample replacement, listing what it will do.

    The size change, the other banks holding the same slot and the SPU budget
    used to arrive as three dialogs in a row, each answerable only in the dark.
    Here they are one screen: the facts, the one real decision, and Replace."""

    def __init__(
        self, parent, plan: SampleReplacementPlan, file_name: str, bank_label: str,
        retunable_songs: Sequence[int] = (),
    ):
        super().__init__(parent, "Replace sample")
        self.setMinimumWidth(WindowSize.REPLACE_SAMPLE_WIDTH)
        self._plan = plan
        self._retunable_songs = list(retunable_songs)
        self._update_shared = None
        self._retune = None
        self._build_ui(file_name, bank_label)

    def chosen(self) -> ReplaceSampleChoice:
        return ReplaceSampleChoice(
            update_shared_banks=self._update_shared.isChecked() if self._update_shared else False,
            retune_songs=self._retune.isChecked() if self._retune else False,
        )

    def _build_ui(self, file_name: str, bank_label: str) -> None:
        self.add_header(
            f"Replace sample {self._plan.sample_index}",
            f"{self._heading(file_name, bank_label)} {self._size_text()}",
        )

        if self._plan.needs_shared_choice:
            self._body.addWidget(self._shared_group())

        if self._retunable_songs:
            self._body.addLayout(self._retune_option())

        if self._plan.exceeds_bank_limit:
            self._body.addWidget(self.callout(self._plan.bank_size.warning_text))

        if self._exceeds_saphi_cap():
            self._body.addWidget(self._saphi_label())

        self.add_footer(self.buttons("🔁  Replace"))

    def _heading(self, file_name: str, bank_label: str) -> str:
        slot = f"SPU #{self._plan.spu_index}" if self._plan.spu_index is not None else "unknown slot"
        return f"<b>{file_name}</b> replaces it ({slot}) in {bank_label}."

    def _size_text(self) -> str:
        delta = self._plan.size_delta
        if delta == 0:
            return (
                f"Same size as the original ({self._plan.old_byte_size} bytes), so no other "
                f"bank is affected."
            )

        direction = "larger" if delta > 0 else "smaller"
        return (
            f"{abs(delta)} bytes {direction} than the original: "
            f"{self._plan.old_byte_size} → {self._plan.new_byte_size} bytes."
        )

    def _shared_group(self) -> QGroupBox:
        impacts = self._plan.shared_impacts
        banks = ", ".join(
            impact.bank_name or f"Bank {impact.bank_index}" for impact in impacts
        )
        carry = "carries its" if len(impacts) == 1 else "carry their"
        them = "it needs" if len(impacts) == 1 else "they need"
        their = "its samples" if len(impacts) == 1 else "their samples"

        group = QGroupBox("This sample is shared")
        box = QVBoxLayout(group)

        box.addWidget(self.hint(
            f"{banks} {carry} own copy of this slot. Changing its size re-cuts "
            f"that blob too, so {them} rebuilding or {their} break."
        ))

        other = "that bank" if len(impacts) == 1 else "those banks"
        self._update_shared = QRadioButton(f"Update {other} as well (recommended)")
        self._update_shared.setChecked(True)
        box.addWidget(self._update_shared)

        left_alone = "the other one" if len(impacts) == 1 else "the others"
        box.addWidget(QRadioButton(f"Replace in this bank only — leaves {left_alone} mis-cut"))

        return group

    def _retune_option(self) -> QVBoxLayout:
        """Offered only when the new file's rate differs from the one the
        songs already play this sample at — otherwise there is nothing to
        decide."""
        songs = ", ".join(str(i) for i in self._retunable_songs)
        noun = "song" if len(self._retunable_songs) == 1 else "songs"
        self._retune = QCheckBox(f"Retune {noun} {songs} to the new file's sample rate")
        self._retune.setChecked(True)

        return self.option_with_hint(
            self._retune,
            "Each instrument and percussion playing this sample is scaled by "
            "new rate ÷ old rate, so variants at different pitches stay the "
            "same interval apart. Untick to keep the current pitch values.",
        )

    def _exceeds_saphi_cap(self) -> bool:
        return len(self._plan.new_blob) > SAPHI_BANK_MAX_SIZE

    def _saphi_label(self) -> QLabel:
        over = len(self._plan.new_blob) - SAPHI_BANK_MAX_SIZE
        return self.callout(
            f"The bank would be {len(self._plan.new_blob)} bytes — {over} over Saphi's "
            f"{SAPHI_BANK_MAX_SIZE}-byte limit, so Saphi would reject the export."
        )
