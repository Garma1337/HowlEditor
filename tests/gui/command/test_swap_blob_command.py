# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.ctr.formats.howl.models import HowlFile, OtherFX, SpuAddrEntry
from howl_editor.gui.command.swap_blob_command import SwapBlobCommand


class FakeWindow:
    def __init__(self, hwl: HowlFile):
        self.hwl = hwl
        self.changes = []

    def apply_change(self, change) -> None:
        self.changes.append(change)


@pytest.fixture
def window(bank_builder) -> FakeWindow:
    return FakeWindow(HowlFile(spu_addrs=[SpuAddrEntry(0, 2)], banks=[bank_builder.merge([])]))


def _add_sample(window, bank_builder, bank_reader, spu_index: int):
    """Add a sample the way the handler does, returning the pre-write table."""
    before = list(window.hwl.spu_addrs)
    blob = bank_builder.add_sample(
        window.hwl.banks[0], window.hwl.spu_addrs, b"\x11" * 32, bank_reader,
        spu_index=spu_index,
    )
    return before, blob


def _sample_slots(window, bank_reader) -> list[int]:
    return [s.spu_index for s in bank_reader.parse(window.hwl.banks[0], window.hwl.spu_addrs)]


class TestSpuTableAcrossUndoRedo:

    def test_undo_drops_the_slot_the_sample_added(self, window, bank_builder, bank_reader):
        before, blob = _add_sample(window, bank_builder, bank_reader, spu_index=1)
        command = SwapBlobCommand(window, "add", HowlCollection.BANKS, 0, blob, old_spu=before)
        command.redo()

        command.undo()

        assert len(window.hwl.spu_addrs) == 1
        assert _sample_slots(window, bank_reader) == []

    def test_redo_brings_the_slot_back_with_the_sample(self, window, bank_builder, bank_reader):
        before, blob = _add_sample(window, bank_builder, bank_reader, spu_index=1)
        command = SwapBlobCommand(window, "add", HowlCollection.BANKS, 0, blob, old_spu=before)
        command.redo()
        command.undo()

        command.redo()

        assert window.hwl.spu_addrs[1].byte_size == 32
        assert _sample_slots(window, bank_reader) == [1]

    def test_reusing_a_free_slot_restores_its_old_size_on_undo(self, window, bank_builder, bank_reader):
        window.hwl.spu_addrs.append(SpuAddrEntry(0, 9))   # free slot, 72 bytes
        before, blob = _add_sample(window, bank_builder, bank_reader, spu_index=1)
        command = SwapBlobCommand(window, "add", HowlCollection.BANKS, 0, blob, old_spu=before)
        command.redo()

        command.undo()

        assert window.hwl.spu_addrs[1].size == 9

    def test_commands_without_a_snapshot_leave_the_table_alone(self, window, bank_builder):
        command = SwapBlobCommand(window, "song", HowlCollection.BANKS, 0, b"\x00" * 8)

        command.redo()
        command.undo()

        assert [e.size for e in window.hwl.spu_addrs] == [2]


class TestOtherFxAcrossUndoRedo:
    """A sample's rate lives in OtherFX, so an edit that records one has to
    take it back on undo - otherwise the slot stays referenced forever."""

    def _attach(self, window, pitch: int) -> list[OtherFX]:
        before = [OtherFX(**vars(fx)) for fx in window.hwl.other_fx]
        window.hwl.other_fx.append(OtherFX(pitch=pitch, spu_index=1))
        return before

    def test_undo_removes_an_added_entry(self, window):
        before = self._attach(window, 0x0800)
        command = SwapBlobCommand(window, "add", HowlCollection.BANKS, 0, bytes(32), old_fx=before)
        command.redo()

        command.undo()

        assert window.hwl.other_fx == []

    def test_redo_brings_it_back(self, window):
        before = self._attach(window, 0x0800)
        command = SwapBlobCommand(window, "add", HowlCollection.BANKS, 0, bytes(32), old_fx=before)
        command.redo()
        command.undo()

        command.redo()

        assert [(fx.spu_index, fx.pitch) for fx in window.hwl.other_fx] == [(1, 0x0800)]

    def test_undo_restores_a_changed_pitch(self, window):
        window.hwl.other_fx.append(OtherFX(pitch=0x0400, spu_index=1))
        before = [OtherFX(**vars(fx)) for fx in window.hwl.other_fx]
        window.hwl.other_fx[0].pitch = 0x1000
        command = SwapBlobCommand(window, "replace", HowlCollection.BANKS, 0, bytes(32), old_fx=before)
        command.redo()

        command.undo()

        assert window.hwl.other_fx[0].pitch == 0x0400

    def test_an_added_entry_rebuilds_the_lists(self, window):
        before = self._attach(window, 0x0800)
        command = SwapBlobCommand(window, "add", HowlCollection.BANKS, 0, bytes(32), old_fx=before)

        command.redo()

        assert window.changes[-1].structural


class TestWhatTheViewsAreTold:
    """A command reports what it changed so the views repaint that row instead
    of rebuilding themselves."""

    def test_an_in_place_swap_names_the_blob_it_replaced(self, window):
        command = SwapBlobCommand(window, "swap", HowlCollection.BANKS, 0, bytes(32))

        command.redo()

        assert window.changes[-1].collection == HowlCollection.BANKS
        assert window.changes[-1].index == 0

    def test_it_is_not_structural_so_no_index_moved(self, window):
        command = SwapBlobCommand(window, "swap", HowlCollection.BANKS, 0, bytes(32))

        command.redo()

        assert not window.changes[-1].structural

    def test_undo_reports_the_same_change_as_redo(self, window):
        """Otherwise undoing would reset the UI that the edit left alone."""
        command = SwapBlobCommand(window, "swap", HowlCollection.BANKS, 0, bytes(32))

        command.redo()
        command.undo()

        assert window.changes[-1] == window.changes[-2]
