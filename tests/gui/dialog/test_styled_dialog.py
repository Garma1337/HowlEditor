# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QListWidget

from howl_editor.gui.dialog.choice_dialog import ChoiceDialog, ChoiceField
from howl_editor.gui.dialog.number_dialog import NumberDialog
from howl_editor.gui.dialog.styled_dialog import StyledDialog


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


class TestButtons:

    def test_primary_action_carries_its_verb_and_is_marked(self, qt_app):
        box = StyledDialog(None, "t").buttons("🔁  Replace")
        primary = next(b for b in box.buttons() if box.buttonRole(b) == QDialogButtonBox.AcceptRole)

        assert primary.text() == "🔁  Replace"
        assert primary.property("primary") is True
        assert primary.isDefault()

    def test_a_primary_action_comes_with_cancel(self, qt_app):
        box = StyledDialog(None, "t").buttons("🔁  Replace")
        rejects = [b.text() for b in box.buttons() if box.buttonRole(b) == QDialogButtonBox.RejectRole]

        assert rejects == ["✖️  Cancel"]

    def test_without_a_primary_the_box_only_closes(self, qt_app):
        box = StyledDialog(None, "t").buttons()

        assert [box.buttonRole(b) for b in box.buttons()] == [QDialogButtonBox.RejectRole]

    def test_accept_hook_replaces_the_plain_accept(self, qt_app):
        dialog = StyledDialog(None, "t")
        calls = []
        box = dialog.buttons("Go", on_accept=lambda: calls.append(1))

        box.accepted.emit()

        assert calls == [1]
        assert dialog.result() != QDialog.Accepted

    def test_secondary_buttons_never_take_the_enter_key(self, qt_app):
        assert StyledDialog(None, "t").action_button("Preview").autoDefault() is False


class TestCallout:

    def test_hidden_while_empty(self, qt_app):
        assert StyledDialog(None, "t").callout().isHidden()

    def test_filling_it_shows_it_and_clearing_hides_it(self, qt_app):
        dialog = StyledDialog(None, "t")
        callout = dialog.callout()

        dialog.set_callout(callout, "Bank too big")
        assert not callout.isHidden()

        dialog.set_callout(callout, "")
        assert callout.isHidden()

    def test_carries_its_severity_for_the_stylesheet(self, qt_app):
        callout = StyledDialog(None, "t").callout("x", StyledDialog.DANGER)

        assert callout.property("severity") == "danger"


class TestFooter:

    def test_a_dialog_without_a_list_soaks_up_spare_height_above_the_buttons(self, qt_app):
        dialog = StyledDialog(None, "t")
        dialog.add_header("Title")
        dialog.add_footer(dialog.buttons("OK"))

        assert dialog._has_stretch()

    def test_a_dialog_with_a_list_lets_the_list_take_it(self, qt_app):
        dialog = StyledDialog(None, "t")
        dialog._body.addWidget(QListWidget(), stretch=1)
        count = dialog._body.count()

        dialog.add_footer(dialog.buttons("OK"))

        # Only the footer gap and row were added - no stretch competing with the list.
        assert dialog._body.count() == count + 2


class TestChoiceDialog:

    def test_reports_the_pick_in_each_field(self, qt_app):
        dialog = ChoiceDialog(None, "Validate", "", [
            ChoiceField("Bank:", ["a", "b"]),
            ChoiceField("Song:", ["x", "y", "z"], current=2),
        ])

        assert dialog.chosen() == [0, 2]


class TestNumberDialog:

    def test_starts_at_the_given_value_within_range(self, qt_app):
        dialog = NumberDialog(None, "Set volume", "", "Volume:", 300, 0, 255)

        assert dialog.value() == 255
