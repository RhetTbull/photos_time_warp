"""Support for colorized output for photos_time_warp"""

from collections import namedtuple
from typing import Callable, List

from rich.themes import Theme


def add_rich_markup_tag(tag: str) -> str:
    """Add rich markup tags to string"""

    def add_tag(msg: str) -> str:
        """Add tag to string"""
        return f"[{tag}]{msg}[/{tag}]"

    return add_tag


def no_markup(msg: str) -> str:
    """Return msg without markup"""
    return msg


color_functions = namedtuple(
    "color_functions", ["change", "no_change", "uuid", "filename", "time"]
)

color_themes = {
    "dark": Theme(
        {
            "change": "bold bright_red",
            "no_change": "bold bright_green",
            "uuid": "bold dark_orange",
            "filename": "bold bright_magenta",
            "time": "bold dodger_blue1",
            "tz": "bold bright_cyan",
        }
    ),
    "light": Theme(
        {
            "change": "bold dark_red",
            "no_change": "bold dark_green",
            "uuid": "bold orange_red1",
            "filename": "bold dark_magenta",
            "time": "bold blue1",
            "tz": "bold cyan",
        }
    ),
    "mono": Theme(
        {
            "change": "reverse",
            "no_change": "",
            "uuid": "",
            "filename": "",
            "time": "",
            "tz": "",
        }
    ),
    "plain": Theme(
        {
            "change": "",
            "no_change": "",
            "uuid": "",
            "filename": "",
            "time": "",
            "tz": "",
        }
    ),
}
color_themes["default"] = color_themes["dark"]