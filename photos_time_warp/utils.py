"""Utils for photos_time_warp"""


def pluralize(count, singular, plural):
    """Return singular or plural based on count"""
    if count == 1:
        return singular
    else:
        return plural


def noop(*args, **kwargs):
    """No-op function for use as verbose if verbose not set"""
    pass


def add_rich_markup_tag(tag: str) -> str:
    """Add rich markup tags to string"""

    def add_tag(msg: str) -> str:
        """Add tag to string"""
        return f"[{tag}]{msg}[/{tag}]"

    return add_tag


red = add_rich_markup_tag("red")

green = add_rich_markup_tag("green")

bright_red = add_rich_markup_tag("bright_red")

bright_green = add_rich_markup_tag("bright_green")

dark_orange = add_rich_markup_tag("dark_orange")

dark_magenta = add_rich_markup_tag("dark_magenta")

bright_magenta = add_rich_markup_tag("bright_magenta")

change_color = bright_red

no_change_color = bright_green

uuid_color = dark_orange

filename_color = bright_magenta
