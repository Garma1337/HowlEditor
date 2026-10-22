# coding: utf-8

from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem

from howl_editor.ctr.diagnostics.howl_diagnostics import DiagnosisReport, Severity
from howl_editor.gui.dialog.styled_dialog import StyledDialog
from howl_editor.gui.layout import WindowSize
from howl_editor.gui.severity_presenter import SeverityPresenter


class DiagnosisReportDialog(StyledDialog):
    """Shows a whole-file diagnosis: a severity-count header and every finding,
    most severe first, with a button to copy the report as plain text."""

    def __init__(self, parent, report: DiagnosisReport, severity_presenter: SeverityPresenter | None = None):
        super().__init__(parent, "HOWL Diagnosis")
        self.resize(WindowSize.DIAGNOSIS_WIDTH, WindowSize.DIAGNOSIS_HEIGHT)
        self._report = report
        self._presenter = severity_presenter or SeverityPresenter()
        self._build_ui()

    def _icon(self, severity: Severity) -> str:
        return self._presenter.emoji(severity)

    def _build_ui(self) -> None:
        counts = self._report.counts()
        summary = (
            f"{self._icon(Severity.ERROR)} {counts[Severity.ERROR]} errors  ·  "
            f"{self._icon(Severity.WARNING)} {counts[Severity.WARNING]} warnings  ·  "
            f"{self._icon(Severity.INFO)} {counts[Severity.INFO]} info"
        )

        if counts[Severity.ERROR] == 0 and counts[Severity.WARNING] == 0:
            subtitle = f"{summary}<br>No issues found. 🎉"
        else:
            subtitle = f"{summary}<br>Items that may crash the game or sound wrong in-game:"

        self.add_header("HOWL diagnosis", subtitle)

        self._list = QListWidget()
        self._list.setWordWrap(True)
        self._body.addWidget(self._list, stretch=1)
        self._populate()

        self.add_footer(
            self.buttons("✅  Done", cancel=False),
            self.action_button("📋  Copy to clipboard", on_click=self._copy_to_clipboard),
        )

    def _populate(self) -> None:
        for finding in self._report.findings:
            icon = self._icon(finding.severity)
            item = QListWidgetItem(f"{icon}  [{finding.category.value}]  {finding.message}")
            self._list.addItem(item)

    def _plain_text(self) -> str:
        lines = []
        counts = self._report.counts()
        lines.append(
            f"HOWL Diagnosis — {counts[Severity.ERROR]} errors, "
            f"{counts[Severity.WARNING]} warnings, {counts[Severity.INFO]} info"
        )
        lines.append("")
        for finding in self._report.findings:
            lines.append(f"[{finding.severity.name}] {finding.category.value}: {finding.message}")
        return "\n".join(lines)

    def _copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self._plain_text())
