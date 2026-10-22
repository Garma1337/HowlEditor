# coding: utf-8

from dataclasses import replace

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.gui.howl_change import HowlChange
from howl_editor.ctr.formats.howl.models import OtherFX, SpuAddrEntry


class SwapBlobCommand(QUndoCommand):
    """
    Replaces a bank or song blob, with optional spu_addrs snapshot for sample operations.

    Covers: replace bank, replace song, add/remove/replace sample, add/remove/replace sequence.
    """

    def __init__(
        self,
        window,
        description: str,
        collection: HowlCollection,
        index: int,
        new_blob: bytes,
        snapshot_spu: bool = False,
        old_spu: list[SpuAddrEntry] | None = None,
        old_fx: list[OtherFX] | None = None,
    ):
        super().__init__(description)
        self._window = window
        self._collection = collection
        self._index = index
        self._old_blob = self._get_list()[index]
        self._new_blob = new_blob
        self._old_spu = self._capture_spu(window, snapshot_spu, old_spu)
        self._new_spu = self._copy(window.hwl.spu_addrs) if self._old_spu is not None else None
        self._old_fx = self._copy_fx(old_fx) if old_fx is not None else None
        self._new_fx = self._copy_fx(window.hwl.other_fx) if old_fx is not None else None

    def _capture_spu(
        self, window, snapshot_spu: bool, old_spu: list[SpuAddrEntry] | None,
    ) -> list[SpuAddrEntry] | None:
        if old_spu is not None:
            return self._copy(old_spu)

        if not snapshot_spu:
            return None

        return self._copy(window.hwl.spu_addrs)

    def redo(self):
        self._get_list()[self._index] = self._new_blob
        self._restore(self._new_spu)
        self._restore_fx(self._new_fx)
        self._window.apply_change(self._change())

    def undo(self):
        self._get_list()[self._index] = self._old_blob
        self._restore(self._old_spu)
        self._restore_fx(self._old_fx)
        self._window.apply_change(self._change())

    def _change(self) -> HowlChange:
        """The blob is swapped in place, so no index moves and the views can
        repaint the one row this touched. Undo reports the same thing as redo -
        otherwise undoing would reset the UI the edit just left alone.

        An FX change reaches past the one blob, and adding an entry renumbers
        the Effects list."""
        if self._old_fx is not None:
            return HowlChange(structural=len(self._old_fx) != len(self._new_fx))

        return HowlChange(collection=self._collection, index=self._index)

    def _restore(self, snapshot: list[SpuAddrEntry] | None) -> None:
        """A sample exists only while its slot entry does, so both directions
        move the table with the blob."""
        if snapshot is not None:
            self._window.hwl.spu_addrs[:] = self._copy(snapshot)

    def _restore_fx(self, snapshot: list[OtherFX] | None) -> None:
        if snapshot is not None:
            self._window.hwl.other_fx[:] = self._copy_fx(snapshot)

    def _copy_fx(self, entries: list[OtherFX]) -> list[OtherFX]:
        return [replace(fx) for fx in entries]

    def _copy(self, entries: list[SpuAddrEntry]) -> list[SpuAddrEntry]:
        return [SpuAddrEntry(e.ptr, e.size) for e in entries]

    def _get_list(self) -> list:
        return getattr(self._window.hwl, self._collection)
