"""Terminal color helpers."""

import os
import re


class Colors:
    """ANSI color codes for terminal output.

    Respects NO_COLOR environment variable (https://no-color.org/).
    Set NO_COLOR=1 to disable all color output.
    """

    # Check if colors should be disabled
    _colors_disabled = os.environ.get("NO_COLOR") is not None

    GREEN = "" if _colors_disabled else "\033[92m"
    BLUE = "" if _colors_disabled else "\033[94m"
    CYAN = "" if _colors_disabled else "\033[96m"
    YELLOW = "" if _colors_disabled else "\033[93m"
    RED = "" if _colors_disabled else "\033[91m"
    BOLD = "" if _colors_disabled else "\033[1m"
    DIM = "" if _colors_disabled else "\033[2m"
    HIGHLIGHT = "" if _colors_disabled else "\033[93m\033[1m"  # Bright yellow bold
    RESET = "" if _colors_disabled else "\033[0m"


ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text):
    return ANSI_RE.sub("", text)
