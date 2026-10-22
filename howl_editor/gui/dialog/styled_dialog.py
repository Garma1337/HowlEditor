# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QVBoxLayout, QWidget,
)

from howl_editor.gui.layout import DialogSpacing


class StyledDialog(QDialog):
    """Shared frame for the editor's dialogs: a title and subtitle up top, the
    content in the middle, and a footer whose main action stands out.

    Everything that makes the dialogs look alike lives here and in app.qss
    (keyed on the object names set below), so a dialog only decides what it
    shows."""

    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"

    def __init__(self, parent, window_title: str):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(*(DialogSpacing.MARGIN,) * 4)
        self._body.setSpacing(DialogSpacing.SECTION)

    def add_header(self, title: str, subtitle: str = "") -> QLabel:
        """Title in bold above a muted subtitle. Returns the subtitle label so
        a dialog whose description depends on its inputs can update it."""
        header = QVBoxLayout()
        header.setSpacing(DialogSpacing.HEADER)

        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        title_label.setWordWrap(True)
        header.addWidget(title_label)

        subtitle_label = self.hint(subtitle)
        subtitle_label.setVisible(bool(subtitle))
        header.addWidget(subtitle_label)

        self._body.addLayout(header)
        return subtitle_label

    def hint(self, text: str = "") -> QLabel:
        """Secondary text: explanations, units, what a value means."""
        label = QLabel(text)
        label.setObjectName("dialogHint")
        label.setWordWrap(True)
        return label

    def callout(self, text: str = "", severity: str = WARNING) -> QLabel:
        """A tinted box for something the user should not miss. Hidden while
        empty, so a dialog can keep one around and fill it on demand."""
        label = QLabel(text)
        label.setObjectName("dialogCallout")
        label.setProperty("severity", severity)
        label.setWordWrap(True)
        label.setVisible(bool(text))
        return label

    def set_callout(self, label: QLabel, text: str) -> None:
        label.setText(text)
        label.setVisible(bool(text))

    def option_with_hint(self, option: QWidget, text: str) -> QVBoxLayout:
        """A checkbox or radio button with its explanation underneath, lined
        up with the option's text rather than its indicator."""
        layout = QVBoxLayout()
        layout.setSpacing(DialogSpacing.HEADER)
        layout.addWidget(option)

        hint = self.hint(text)
        hint.setIndent(DialogSpacing.OPTION_HINT_INDENT)
        layout.addWidget(hint)
        return layout

    def pick_list(self) -> QListWidget:
        """A list of one-line entries to choose from, with compact rows."""
        widget = QListWidget()
        widget.setObjectName("dialogList")
        return widget

    def section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("dialogSection")
        return label

    def form(self) -> QFormLayout:
        form = QFormLayout()
        form.setHorizontalSpacing(DialogSpacing.FORM_COLUMNS)
        form.setVerticalSpacing(DialogSpacing.FORM_ROWS)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        return form

    def buttons(
        self, primary_text: str | None = None, cancel: bool = True,
        on_accept=None,
    ) -> QDialogButtonBox:
        """The dialog's closing buttons. With `primary_text` there is an
        accept button carrying that verb, drawn as the main action; without
        it the box only closes. `on_accept` replaces the plain accept, for a
        dialog that validates first."""
        box = QDialogButtonBox()

        if primary_text is not None:
            primary = box.addButton(primary_text, QDialogButtonBox.AcceptRole)
            primary.setProperty("primary", True)
            primary.setDefault(True)

        if cancel:
            box.addButton(
                "✖️  Cancel" if primary_text is not None else "✖️  Close",
                QDialogButtonBox.RejectRole,
            )

        box.accepted.connect(on_accept or self.accept)
        box.rejected.connect(self.reject)
        return box

    def add_footer(self, buttons: QDialogButtonBox, *leading: QWidget) -> None:
        """Bottom row: optional secondary actions on the left, the closing
        buttons on the right."""
        row = QHBoxLayout()
        row.setSpacing(DialogSpacing.BUTTONS)

        for widget in leading:
            row.addWidget(widget)

        row.addStretch(1)
        row.addWidget(buttons)

        # A dialog with nothing stretchable would spread spare height into the
        # gaps between its rows; this takes it up above the buttons instead.
        if not self._has_stretch():
            self._body.addStretch(1)

        self._body.addSpacing(DialogSpacing.FOOTER_GAP)
        self._body.addLayout(row)

    def _has_stretch(self) -> bool:
        """True when something already takes up spare height: a stretch
        factor or an expanding spacer (a fixed `addSpacing` gap does not)."""
        for i in range(self._body.count()):
            spacer = self._body.itemAt(i).spacerItem()

            if self._body.stretch(i) > 0 or (
                spacer is not None and spacer.expandingDirections() & Qt.Vertical
            ):
                return True

        return False

    def action_button(self, text: str, tooltip: str = "", on_click=None) -> QPushButton:
        """A secondary button. It never becomes the Enter-key default, so the
        primary action keeps that role however the user tabs around."""
        button = QPushButton(text)
        button.setAutoDefault(False)

        if tooltip:
            button.setToolTip(tooltip)

        if on_click is not None:
            button.clicked.connect(on_click)

        return button
