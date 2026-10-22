# coding: utf-8


class IconSize:
    """Icon dimensions in pixels."""

    LEAF = 22            # leaf-row icons (samples, sequences) + hub-combo dropdown
    ENTRY = 32           # entry-row icons (tracks, banks, FX)
    CATEGORY_TITLE = 40  # category detail-view title icon
    CARD = 64            # category-card grid icons


class ButtonWidth:
    """Fixed pixel widths for buttons that need a stable footprint."""

    # Leaf-row action buttons (icon-only).
    LEAF_PLAY = 32
    LEAF_ACTIONS = 52    # extra width covers Qt's menu indicator arrow

    # Entry-row action buttons (icon-only).
    ENTRY_TOGGLE = 26
    ENTRY_ACTIONS = 56   # extra width covers Qt's menu indicator arrow
    HUB_PLAY = 122

    # Category navigation.
    BACK = 130

    # Player widget.
    PLAYER_BUTTON = 32
    PLAYER_TIME = 90
    PLAYER_LABEL_MIN = 100


class WindowSize:
    """Default startup sizes for the main window and standalone dialogs."""

    MAIN_WIDTH = 1300
    MAIN_HEIGHT = 900

    # Dialogs sized by their content: minimum widths only.
    SAPHI_EXPORT_WIDTH = 440
    EXPORT_WIDTH = 340
    REPLACE_SAMPLE_WIDTH = 520
    COPY_SAMPLE_WIDTH = 460
    EDIT_INSTRUMENT_WIDTH = 460
    MIDI_EXPORT_WIDTH = 440
    CHOICE_WIDTH = 420

    # Dialogs built around a list or table: a starting size.
    SELECT_SAMPLE_WIDTH = 520
    SELECT_SAMPLE_HEIGHT = 560

    TRACK_EVENTS_WIDTH = 820
    TRACK_EVENTS_HEIGHT = 600

    MERGE_BANK_WIDTH = 780
    MERGE_BANK_HEIGHT = 580

    CONVERT_MIDI_WIDTH = 820
    CONVERT_MIDI_HEIGHT = 600

    DIAGNOSIS_WIDTH = 760
    DIAGNOSIS_HEIGHT = 520


class DialogSpacing:
    """Spacing shared by every StyledDialog, so they line up with each other."""

    MARGIN = 20          # around the dialog's content
    SECTION = 14         # between header, sections and footer
    HEADER = 4           # title to subtitle
    FORM_COLUMNS = 16    # form label to field
    FORM_ROWS = 10
    BUTTONS = 8
    FOOTER_GAP = 6       # extra air above the button row
    OPTION_HINT_INDENT = 24  # past a checkbox's indicator, to its text


class Inset:
    """Reusable inset / padding values."""

    BODY = 8  # default inset for entry-row body content
