# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.ctr.formats.bank.models import BankSample
from howl_editor.ctr.formats.cseq.models import CseqInstrument
from howl_editor.ctr.formats.howl.models import HowlFile, OtherFX, SpuAddrEntry
from howl_editor.gui.dialog.replace_sample_dialog import ReplaceSampleChoice
from howl_editor.gui.main_window import MainWindow
from howl_editor.services import container
from tests.conftest import build_bank_blob, build_cseq_bytes

SOURCE_PITCH = 0x0800
TARGET_PITCH = 0x1000


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    """SPU #0 plays at SOURCE_PITCH, SPU #1 at TARGET_PITCH, which the song
    also plays it an octave above. Slot 3 is free."""
    window = MainWindow(container)
    window.hwl = HowlFile(
        spu_addrs=[SpuAddrEntry(0, 2) for _ in range(4)],
        other_fx=[OtherFX(1, 128, SOURCE_PITCH, 0, 100), OtherFX(1, 128, TARGET_PITCH, 1, 100)],
        banks=[build_bank_blob([0, 1], [b"\x00" * 16] * 2) for _ in range(2)],
        songs=[build_cseq_bytes(instruments=[
            CseqInstrument(sample_id=1, frequency=TARGET_PITCH),
            CseqInstrument(sample_id=1, frequency=TARGET_PITCH * 2),
        ])],
    )
    window._rebuild_tree()
    return window


def _source() -> BankSample:
    return BankSample(spu_index=0, data=b"\x00" * 16)


def _song_pitches(window) -> list[int]:
    cseq = container.resolve("cseq_reader").read(window.hwl.songs[0])
    return [inst.frequency for inst in cseq.instruments]


def _fx(window) -> list[tuple[int, int]]:
    return [(fx.spu_index, fx.pitch) for fx in window.hwl.other_fx]


class TestCopyIntoNewSlot:

    def _copy(self, window, monkeypatch):
        monkeypatch.setattr(window._sample_handler, "_pick_new_slot", lambda *a, **k: 3)
        window._sample_handler._apply_copy(_source(), 1, None)

    def test_new_slot_plays_at_the_source_pitch(self, window, monkeypatch):
        self._copy(window, monkeypatch)

        assert (3, SOURCE_PITCH) in _fx(window)

    def test_undo_drops_the_fx_entry(self, window, monkeypatch):
        before = _fx(window)
        self._copy(window, monkeypatch)

        window._undo_stack.undo()

        assert _fx(window) == before


class TestCopyOverSample:

    def _copy_over(self, window, monkeypatch, retune: bool):
        monkeypatch.setattr(
            window._sample_handler, "_confirm_replacement",
            lambda *a, **k: ReplaceSampleChoice(update_shared_banks=False, retune_songs=retune),
        )
        window._sample_handler._apply_copy(_source(), 1, 1)

    def test_songs_follow_the_source_pitch(self, window, monkeypatch):
        self._copy_over(window, monkeypatch, retune=True)

        assert _song_pitches(window) == [SOURCE_PITCH, SOURCE_PITCH * 2]

    def test_unticked_keeps_the_song_pitches(self, window, monkeypatch):
        self._copy_over(window, monkeypatch, retune=False)

        assert _song_pitches(window) == [TARGET_PITCH, TARGET_PITCH * 2]

    def test_one_undo_restores_the_songs(self, window, monkeypatch):
        self._copy_over(window, monkeypatch, retune=True)

        window._undo_stack.undo()

        assert _song_pitches(window) == [TARGET_PITCH, TARGET_PITCH * 2]

    def test_one_undo_restores_the_fx_pitch(self, window, monkeypatch):
        self._copy_over(window, monkeypatch, retune=True)
        assert (1, SOURCE_PITCH) in _fx(window)

        window._undo_stack.undo()

        assert (1, TARGET_PITCH) in _fx(window)
