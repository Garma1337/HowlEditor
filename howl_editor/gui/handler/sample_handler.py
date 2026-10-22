# coding: utf-8

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from howl_editor.ctr import constants
from howl_editor.ctr.formats.bank.models import BankSample
from howl_editor.ctr.formats.cseq.editor import SampleRetuneResult
from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.ctr.formats.howl.models import OtherFX
from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.command import SwapBlobCommand
from howl_editor.gui.dialog.copy_target_dialog import (
    CopyTargetContainer, CopyTargetDialog,
)
from howl_editor.gui.dialog.replace_sample_dialog import ReplaceSampleChoice, ReplaceSampleDialog
from howl_editor.gui.dialog.select_sample_dialog import SelectSampleDialog
from howl_editor.ps1.formats.vag.models import VagSample
from howl_editor.saphi.constants import SAPHI_BANK_MAX_SIZE


class SampleHandler:

    def __init__(self, window):
        self._window = window

    def _bank_within_limit(self, index: int, blob) -> bool:
        """See BankHandler._bank_within_limit."""
        guard = self._window._services.resolve("bank_size_guard")
        return guard is None or self._window.confirm_within_limit(
            guard.check(self._window.hwl, index, blob),
        )

    def export_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        try:
            samples = self._window._services.resolve("bank_reader").parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            path, _ = QFileDialog.getSaveFileName(
                self._window, f"Export Sample SPU {sample.spu_index}",
                f"sample_{sample.spu_index}{FileFormatRegistry.VAG.extension}", FileFormatRegistry.VAG.file_filter,
            )

            if path:
                rate = (
                    self._window._services.resolve("sample_lookup").known_sample_rate(self._window.hwl, sample.spu_index)
                    or self._window._services.resolve("vag_rate_provider").rate
                )
                self._window._services.resolve("vag_writer").write_file(VagSample(sample_rate=rate, data=sample.data), path)
                self._window._notify(f"Exported SPU {sample.spu_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def export_sample_as_wav(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        try:
            samples = self._window._services.resolve("bank_reader").parse(self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs)
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            path, _ = QFileDialog.getSaveFileName(
                self._window, f"Export WAV SPU {sample.spu_index}",
                f"sample_{sample.spu_index}{FileFormatRegistry.WAV.extension}", FileFormatRegistry.WAV.file_filter,
            )

            if path:
                rate = (
                    self._window._services.resolve("sample_lookup").known_sample_rate(self._window.hwl, sample.spu_index)
                    or self._window._services.resolve("vag_rate_provider").rate
                )
                wav = self._window._services.resolve("vag_decoder").decode_to_wav(sample.data, rate)
                Path(path).write_bytes(wav)
                self._window._notify(f"Exported SPU {sample.spu_index} as WAV")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Export failed:\n{e}")

    def add_sample(self, bank_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Add Sample to Bank", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)",
        )

        if path:
            self.add_sample_from_file(bank_index, path)

    def add_sample_from_file(self, bank_index: int, path: str):
        """Add a VAG to a bank in the SPU slot the user picks."""
        if not self._window.hwl:
            return

        try:
            vag = self._window._services.resolve("vag_reader").read_file(path)
            spu_index = self._pick_new_slot(f"Add {Path(path).name} to {self._bank_display(bank_index)}")

            if spu_index is None:
                return

            # add_sample writes the SPU entry in place; keep a restore point so
            # declining the residency guard leaves no dangling entry behind.
            spu_before = list(self._window.hwl.spu_addrs)
            new_blob = self._window._services.resolve("bank_builder").add_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                vag.data, self._window._services.resolve("bank_reader"), spu_index=spu_index,
            )

            if not self._bank_within_limit(bank_index, new_blob):
                self._window.hwl.spu_addrs[:] = spu_before
                return

            fx_before = self._fx_snapshot()
            self._window._services.resolve("howl_editor").attach_sample_rate(self._window.hwl, spu_index, vag.sample_rate)
            self._window._undo_stack.push(
                SwapBlobCommand(
                    self._window, f"Add Sample to Bank {bank_index}", HowlCollection.BANKS, bank_index, new_blob,
                    old_spu=spu_before, old_fx=fx_before,
                ),
            )
            self._window._notify(f"Added sample SPU {spu_index} to bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Add sample failed:\n{e}")

    def _pick_new_slot(self, subject: str, share_spu: int | None = None) -> int | None:
        """Ask which SPU slot a new sample goes into. None when cancelled."""
        choices = self._window._services.resolve("spu_slot_choices")
        hwl = self._window.hwl
        default = choices.default_new_slot(hwl, share_spu)

        if default is None:
            QMessageBox.warning(
                self._window, "No free SPU slot",
                f"All {constants.MAX_SPU_SLOTS} SPU slots are in use, so the new sample has "
                f"nowhere to go. Remove a sample from every bank that holds it to free its "
                f"slot, or replace an existing sample instead.",
            )
            return None

        dialog = SelectSampleDialog(
            self._window,
            title="Pick SPU slot",
            prompt=(
                f"{subject}\n\nPick the SPU slot for the new sample. Slots marked "
                f"🆓 free are unused; greyed-out slots already belong to something else."
            ),
            choices=choices.new_sample_slots(hwl, share_spu),
            current_spu_index=default,
        )

        if dialog.exec() != QDialog.Accepted:
            return None

        return dialog.chosen_spu_index()

    def replace_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(
            self._window, "Replace Sample", "", f"{FileFormatRegistry.VAG.file_filter};;All Files (*)",
        )
        if not path:
            return

        try:
            vag = self._window._services.resolve("vag_reader").read_file(path)
            plan = self._window._services.resolve("sample_replacement_planner").plan(
                self._window.hwl, bank_index, sample_index, vag.data,
            )

            new_pitch = (
                self._window._services.resolve("sample_rate_converter").pitch_for_rate(vag.sample_rate)
                if vag.sample_rate > 0 else None
            )
            retuned_songs = (
                self._retune_songs(plan.spu_index, new_pitch)
                if new_pitch is not None and plan.spu_index is not None else {}
            )
            choice = self._confirm_replacement(
                plan, Path(path).name, bank_index, sorted(retuned_songs),
            )

            if choice is None:
                return

            self._apply_replacement(
                plan, vag.data, choice.update_shared_banks, new_pitch=new_pitch,
                retuned_songs=retuned_songs if choice.retune_songs else None,
            )
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Replace failed:\n{e}")

    def _confirm_replacement(
        self, plan, source_label: str, bank_index: int, retunable_songs: Sequence[int] = (),
    ) -> ReplaceSampleChoice | None:
        """Show the one prompt that covers a sample overwrite. None = cancelled."""
        dialog = ReplaceSampleDialog(
            self._window, plan, source_label, self._bank_display(bank_index),
            retunable_songs,
        )

        if dialog.exec() != QDialog.Accepted:
            return None

        return dialog.chosen()

    def _apply_replacement(
        self, plan, new_data: bytes, update_shared: bool,
        new_pitch: int | None = None, verb: str = "Replaced",
        retuned_songs: dict[int, SampleRetuneResult] | None = None,
    ) -> None:
        """Write the planned replacement. The plan was built against copies, so
        the companion blobs are rebuilt here against the live table — before
        replace_sample moves the size entry."""
        spu_before = list(self._window.hwl.spu_addrs)
        companions = (
            self._window._services.resolve("shared_sample_propagator").rebuild_owners(
                self._window.hwl, spu_before, plan.spu_index, new_data, plan.bank_index,
            )
            if update_shared and plan.spu_index is not None else {}
        )

        new_blob = self._window._services.resolve("bank_builder").replace_sample(
            self._window.hwl.banks[plan.bank_index], self._window.hwl.spu_addrs,
            plan.sample_index, new_data, self._window._services.resolve("bank_reader"),
        )
        fx_before = self._fx_snapshot()

        if new_pitch is not None and plan.spu_index is not None:
            self._window._services.resolve("howl_editor").set_sample_pitch(
                self._window.hwl, plan.spu_index, new_pitch,
            )

        self._push_replacement(plan.bank_index, new_blob, companions, spu_before, fx_before, retuned_songs)
        self._window._notify(
            self._replace_message(plan.bank_index, plan.sample_index, companions, verb, retuned_songs),
        )
        self._warn_if_bank_oversized(plan.bank_index, len(new_blob))

    def _retune_songs(self, spu_index: int, new_pitch: int) -> dict[int, SampleRetuneResult]:
        """song_index → blob with every descriptor playing `spu_index` moved
        onto the new sample's rate. The old sample's rate is taken from the
        pitch the file already plays it at (FX first, as everywhere else), and
        each descriptor is scaled by new/old so pitched variants of one sample
        keep their spacing.

        Must run before the FX pitch is updated, which would otherwise hand
        back the new pitch as the old one."""
        old_pitch = self._known_pitch(spu_index)

        if not old_pitch or new_pitch <= 0 or new_pitch == old_pitch:
            return {}

        editor = self._window._services.resolve("cseq_editor")
        retuned: dict[int, SampleRetuneResult] = {}

        for song_index, song_blob in enumerate(self._window.hwl.songs):
            try:
                result = editor.retune_sample(song_blob, spu_index, new_pitch / old_pitch)
            except Exception:
                continue

            if result is not None:
                retuned[song_index] = result

        return retuned

    def _push_replacement(
        self, bank_index: int, new_blob: bytes, companions: dict[int, bytes],
        spu_before: list, fx_before: list[OtherFX],
        retuned_songs: dict[int, SampleRetuneResult] | None = None,
    ) -> None:
        """One undo step covers the edit and every bank and song dragged along with it,
        so undoing can't leave the file half-propagated."""
        stack = self._window._undo_stack

        # Each push redoes immediately, so without one scope around them the
        # views would update once per bank sharing the sample.
        with self._window.batched_changes():
            grouped = bool(companions or retuned_songs)

            if grouped:
                shared = f" (+{len(companions)} shared)" if companions else ""
                stack.beginMacro(f"Replace Sample in Bank {bank_index}{shared}")

            stack.push(SwapBlobCommand(
                self._window, f"Replace Sample in Bank {bank_index}",
                HowlCollection.BANKS, bank_index, new_blob, old_spu=spu_before, old_fx=fx_before,
            ))

            for other_index, blob in companions.items():
                stack.push(SwapBlobCommand(
                    self._window, f"Update Shared Sample in Bank {other_index}",
                    HowlCollection.BANKS, other_index, blob, snapshot_spu=False,
                ))

            for song_index, result in (retuned_songs or {}).items():
                stack.push(SwapBlobCommand(
                    self._window, f"Retune Song {song_index} to New Sample",
                    HowlCollection.SONGS, song_index, result.blob,
                ))

            if grouped:
                stack.endMacro()

    def _replace_message(
        self, bank_index: int, sample_index: int, companions: dict[int, bytes],
        verb: str = "Replaced", retuned_songs: dict[int, SampleRetuneResult] | None = None,
    ) -> str:
        base = f"{verb} sample {sample_index} in bank {bank_index}"

        if companions:
            base = f"{base} (also updated bank(s) {sorted(companions)})"

        if retuned_songs:
            base = f"{base}; retuned its instruments in song(s) {sorted(retuned_songs)}"
            held = sum(result.held for result in retuned_songs.values())

            if held:
                base = f"{base} — {held} held at the SPU's 4× pitch ceiling"

        return base

    def _find_spu_index(self, bank_index: int, sample_index: int) -> int | None:
        try:
            samples = self._window._services.resolve("bank_reader").parse(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
            )

            if 0 <= sample_index < len(samples):
                return samples[sample_index].spu_index
        except Exception:
            pass

        return None

    def _warn_if_bank_oversized(self, bank_index: int, bank_size: int) -> None:
        if bank_size <= SAPHI_BANK_MAX_SIZE:
            return

        over_by = bank_size - SAPHI_BANK_MAX_SIZE
        self._window._notify(
            f"⚠️ Bank {bank_index} is {bank_size} bytes — {over_by} over the "
            f"Saphi {SAPHI_BANK_MAX_SIZE}-byte limit. Saphi will reject the export.",
            10000,
        )

    def copy_sample(self, src_bank: int, src_sample: int) -> None:
        """Copy a sample's data into another bank — either appended as a new
        sample or replacing an existing slot in the target bank."""
        if not self._window.hwl:
            return

        try:
            src_samples = self._window._services.resolve("bank_reader").parse(
                self._window.hwl.banks[src_bank], self._window.hwl.spu_addrs,
            )

            if src_sample >= len(src_samples):
                return

            src = src_samples[src_sample]
            banks = self._build_copy_bank_summaries()
            size_text = self._window._services.resolve("size_formatter").format_bytes(len(src.data))
            source_display = self._bank_display(src_bank)
            summary = (
                f"Copy sample {src_sample} from {source_display} "
                f"(SPU #{src.spu_index}, {size_text}) to:"
            )
            dialog = CopyTargetDialog(
                self._window,
                title="Copy Sample",
                prompt=summary,
                container_label="Target bank:",
                child_label="Target sample:",
                append_label="(Append as new sample)",
                containers=banks,
                source_container_index=src_bank,
            )

            if dialog.exec() != QDialog.Accepted:
                return

            target = dialog.chosen_target()
            if target is None:
                return

            self._apply_copy(src, target.container_index, target.child_index)
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Copy failed:\n{e}")

    def _build_copy_bank_summaries(self) -> list[CopyTargetContainer]:
        out: list[CopyTargetContainer] = []

        for i, blob in enumerate(self._window.hwl.banks):
            try:
                samples = self._window._services.resolve("bank_reader").parse(blob, self._window.hwl.spu_addrs)
                child_labels = tuple(
                    f"Sample {slot} — SPU #{s.spu_index}"
                    for slot, s in enumerate(samples)
                )
            except Exception:
                child_labels = ()

            out.append(CopyTargetContainer(
                index=i, display=self._bank_display(i), child_labels=child_labels,
            ))

        return out

    def _bank_display(self, index: int) -> str:
        name = self._window._services.resolve("bank_reader").get_name(index)
        return f"Bank {index} — {name}" if name else f"Bank {index}"

    def _apply_copy(
        self, src: BankSample, target_bank: int, target_sample: int | None,
    ) -> None:
        if target_sample is not None:
            self._copy_over_sample(src, target_bank, target_sample)
            return

        target_blob = self._window.hwl.banks[target_bank]
        # Identical audio can share the source's slot — unless the target
        # bank already holds that slot, where sharing would list it twice.
        already_there = src.spu_index in self._window._services.resolve("bank_reader").sample_ids(target_blob)
        spu_index = self._pick_new_slot(
            f"Copy SPU #{src.spu_index} into {self._bank_display(target_bank)}",
            share_spu=None if already_there else src.spu_index,
        )

        if spu_index is None:
            return

        spu_before = list(self._window.hwl.spu_addrs)
        new_blob = self._window._services.resolve("bank_builder").add_sample(
            target_blob, self._window.hwl.spu_addrs,
            src.data, self._window._services.resolve("bank_reader"), spu_index=spu_index,
        )

        if not self._bank_within_limit(target_bank, new_blob):
            self._window.hwl.spu_addrs[:] = spu_before
            return

        fx_before = self._fx_snapshot()
        source_pitch = self._known_pitch(src.spu_index)

        if spu_index != src.spu_index and source_pitch is not None:
            self._window._services.resolve("howl_editor").attach_sample_pitch(
                self._window.hwl, spu_index, source_pitch,
            )

        self._window._undo_stack.push(SwapBlobCommand(
            self._window, f"Copy sample into Bank {target_bank}",
            HowlCollection.BANKS, target_bank, new_blob, old_spu=spu_before, old_fx=fx_before,
        ))

        self._window._notify(
            f"Copied sample into bank {target_bank} as SPU #{spu_index}",
        )
        self._warn_if_bank_oversized(target_bank, len(new_blob))

    def _copy_over_sample(self, src: BankSample, target_bank: int, target_sample: int) -> None:
        """Copying onto an existing sample overwrites a slot exactly as a file
        replacement does, so it takes the same plan and prompt."""
        plan = self._window._services.resolve("sample_replacement_planner").plan(
            self._window.hwl, target_bank, target_sample, src.data,
        )
        source_pitch = self._known_pitch(src.spu_index)
        retuned_songs = (
            self._retune_songs(plan.spu_index, source_pitch)
            if source_pitch is not None and plan.spu_index is not None else {}
        )
        choice = self._confirm_replacement(
            plan, f"SPU #{src.spu_index}", target_bank, sorted(retuned_songs),
        )

        if choice is None:
            return

        self._apply_replacement(
            plan, src.data, choice.update_shared_banks, new_pitch=source_pitch,
            verb="Copied over", retuned_songs=retuned_songs if choice.retune_songs else None,
        )

    def _known_pitch(self, spu_index: int) -> int | None:
        """The pitch the file already plays a sample at, or None when nothing
        references it."""
        return self._window._services.resolve("sample_lookup").sample_pitch_map(
            self._window.hwl,
        ).get(spu_index)

    def _fx_snapshot(self) -> list[OtherFX]:
        """OtherFX as it is now, for an undo step that is about to change it
        in place."""
        return [replace(fx) for fx in self._window.hwl.other_fx]

    def remove_sample(self, bank_index: int, sample_index: int):
        if not self._window.hwl:
            return

        if QMessageBox.question(
            self._window, "Remove Sample", f"Remove sample {sample_index} from bank {bank_index}?",
        ) != QMessageBox.Yes:
            return

        try:
            new_blob = self._window._services.resolve("bank_builder").remove_sample(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
                sample_index, self._window._services.resolve("bank_reader"),
            )
            self._window._undo_stack.push(
                SwapBlobCommand(self._window, f"Remove Sample {sample_index} from Bank {bank_index}", HowlCollection.BANKS, bank_index, new_blob, snapshot_spu=True),
            )
            self._window._notify(f"Removed sample {sample_index} from bank {bank_index}")
        except Exception as e:
            QMessageBox.critical(self._window, "Error", f"Remove failed:\n{e}")
