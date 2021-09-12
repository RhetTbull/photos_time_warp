""" Fix time / date / timezone for photos in Apple Photos """

import datetime
import os
import sys
from functools import partial

import click
import pytimeparse
from cloup import (
    Command,
    Context,
    HelpFormatter,
    HelpTheme,
    Style,
    command,
    constraint,
    option,
    option_group,
    version_option,
)
from cloup.constraints import RequireAtLeast, mutually_exclusive
from osxphotos.exiftool import get_exiftool_path
from photoscript import PhotosLibrary

from ._version import __version__
from .exif_updater import ExifUpdater
from .phototz import PhotoTimeZoneUpdater
from .timeutils import (
    time_string_to_datetime,
    update_datetime,
    utc_offset_string_to_seconds,
)
from .timezones import Timezone

# from rich.console import Console
# from rich.markdown import Markdown


# if True, shows verbose output, controlled via --verbose flag
VERBOSE = False

# name of the script
APP_NAME = "photos_time_warp"


def verbose(message_str, **kwargs):
    if not VERBOSE:
        return
    click.secho(message_str, **kwargs)


def print_help_msg(command):
    with Context(command) as ctx:
        click.echo(command.get_help(ctx))


class DateTimeISO8601(click.ParamType):
    """A datetime string in ISO8601 format"""

    name = "DATETIME"

    def convert(self, value, param, ctx):
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            self.fail(
                f"Invalid datetime format: {value}. "
                "Valid format for datetime: 'YYYY-MM-DD[*HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]]]'"
            )


class TimeString(click.ParamType):
    """A timestring in format HH:MM:SS, HH:MM:SS.fff, HH:MM"""

    name = "TIMESTRING"

    def convert(self, value, param, ctx):
        try:
            return time_string_to_datetime(value)
        except ValueError:
            self.fail(
                f"Invalid time format: {value}. "
                "Valid format for time: 'HH:MM:SS', 'HH:MM:SS.fff', 'HH:MM'"
            )


class DateOffset(click.ParamType):
    """A date offset string in the format ±D days, ±W weeks, ±Y years, ±D where D is days"""

    name = "DATEOFFSET"

    def convert(self, value, param, ctx):
        offset = pytimeparse.parse(value)
        if offset is not None:
            offset = offset / 86400
            return datetime.timedelta(days=offset)

        # could be in format "-1" (negative offset) or "+1" (positive offset)
        try:
            return datetime.timedelta(days=int(value))
        except ValueError:
            self.fail(
                f"Invalid date offset format: {value}. "
                "Valid format for date/time offset: '±D days', '±W weeks', '±D' where D is days "
            )


class TimeOffset(click.ParamType):
    """A time offset string in the format [+-]HH:MM[:SS[.fff[fff]]] or +1 days, -2 hours, -18000, etc"""

    name = "TIMEOFFSET"

    def convert(self, value, param, ctx):
        offset = pytimeparse.parse(value)
        if offset is not None:
            return datetime.timedelta(seconds=offset)

        # could be in format "-18000" (negative offset) or "+18000" (positive offset)
        try:
            return datetime.timedelta(seconds=int(value))
        except ValueError:
            self.fail(
                f"Invalid time offset format: {value}. "
                "Valid format for date/time offset: '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or min), '±S seconds' (or sec), '±S' (where S is seconds)"
            )


class UTCOffset(click.ParamType):
    """A UTC offset timezone in format ±[hh]:[mm], ±[h]:[mm], or ±[hh][mm]"""

    name = "UTC_OFFSET"

    def convert(self, value, param, ctx):
        try:
            offset_seconds = utc_offset_string_to_seconds(value)
            return Timezone(offset_seconds)
        except Exception:
            self.fail(
                f"Invalid timezone format: {value}. "
                "Valid format for timezone offset: '±HH:MM', '±H:MM', or '±HHMM'"
            )


class PhotosTimeWarpCommand(Command):
    """Custom cloup.command that overrides get_help() to show additional help info for photos_time_warp"""

    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        formatter = HelpFormatter()

        formatter.write("\n\n")
        formatter.write_text("")
        help_text += formatter.getvalue()
        return help_text


formatter_settings = HelpFormatter.settings(
    theme=HelpTheme(
        invoked_command=Style(fg="bright_yellow"),
        heading=Style(fg="bright_white", bold=True),
        constraint=Style(fg="magenta"),
        col1=Style(fg="bright_yellow"),
    )
)


@command(cls=PhotosTimeWarpCommand, formatter_settings=formatter_settings)
@option_group(
    "Specify which photo properties to change",
    option(
        "--date",
        metavar="DATE",
        type=DateTimeISO8601(),
        help="Set date for selected photos. Format is 'YYYY-MM-DD'.",
    ),
    option(
        "--date-delta",
        metavar="DELTA",
        type=DateOffset(),
        help="Adjust date for selected photos by DELTA. "
        "Format is one of: '±D days', '±W weeks', '±D' where D is days",
    ),
    option(
        "--time",
        metavar="TIME",
        type=TimeString(),
        help="Set time for selected photos. Format is one of 'HH:MM:SS', 'HH:MM:SS.fff', 'HH:MM'.",
    ),
    option(
        "--time-delta",
        metavar="DELTA",
        type=TimeOffset(),
        help="Adjust time for selected photos by DELTA time. "
        "Format is one of '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or min), '±S seconds' (or sec), '±S' (where S is seconds)",
    ),
    option(
        "--timezone",
        metavar="TIMEZONE",
        type=UTCOffset(),
        help="Set timezone for selected photos as offset from UTC. "
        "Format is one of '±HH:MM', '±H:MM', or '±HHMM'",
    ),
    constraint=RequireAtLeast(1),
)
@constraint(mutually_exclusive, ["date", "date_delta"])
@constraint(mutually_exclusive, ["time", "time_delta"])
@option_group(
    "Settings",
    option("--verbose", "-V", "verbose_", is_flag=True, help="Show verbose output."),
    option(
        "--library",
        "-L",
        metavar="PHOTOS_LIBRARY_PATH",
        type=click.Path(),
        help="Path to Photos library (e.g. '~/Pictures/Photos\ Library.photoslibrary'. "
        f"This is not likely needed as {APP_NAME} will usually be able to locate the path to the open Photos library. "
        "Use --library only if you get an error that the Photos library cannot be located.",
    ),
    option(
        "--exiftool",
        is_flag=True,
        help="Use exiftool to also update the date/time/timezone metadata in the original file in Photos' library. "
        "To use --exiftool, you must have the third-party exiftool utility installed (see https://exiftool.org/). "
        "Using this option modifies the *original* file of the image in your Photos library. "
        "It is possible for originals to be missing from disk (for example, if they've not been downloaded from iCloud); "
        "--exiftool will skip those files which are missing.",
    ),
    option(
        "--exiftool-path",
        type=click.Path(exists=True),
        help="Optional path to exiftool executable (will look in $PATH if not specified).",
    ),
)
@version_option(version=__version__)
def cli(
    date,
    date_delta,
    time,
    time_delta,
    timezone,
    exiftool,
    exiftool_path,
    verbose_,
    library,
):
    """Adjust date/time/timezone of photos in Apple Photos"""
    global VERBOSE
    VERBOSE = verbose_

    if exiftool:
        exiftool_path = exiftool_path or get_exiftool_path()
        verbose(f"exiftool path: {exiftool_path}")

    try:
        photos = PhotosLibrary().selection
        if not photos:
            click.echo("No photos selected")
            sys.exit(0)
    except Exception as e:
        click.secho(
            f"Could not get selected photos. Ensure Photos is open and photos to process are selected. {e}",
            fg="red",
        )
        sys.exit(1)

    update_photo_date_time_ = partial(
        update_photo_date_time,
        date=date,
        time=time,
        date_delta=date_delta,
        time_delta=time_delta,
    )

    if timezone:
        tz_updater = PhotoTimeZoneUpdater(
            timezone, verbose=verbose, library_path=library
        )

    if exiftool:
        exif_updater = ExifUpdater(
            library_path=library, verbose=verbose, exiftool_path=exiftool_path
        )

    click.echo(f"Processing {len(photos)} {pluralize(len(photos), 'photo', 'photos')}")
    # send progress bar output to /dev/null if verbose to hide the progress bar
    fp = open(os.devnull, "w") if VERBOSE else None
    with click.progressbar(photos, file=fp) as bar:
        for p in bar:
            if any([date, time, date_delta, time_delta]):
                update_photo_date_time_(p)
            if timezone:
                tz_updater.update_photo(p)
            if exiftool:
                exif_warn, exif_error = exif_updater.update_photo(
                    p, timezone_offset=timezone
                )
                if exif_warn:
                    click.secho(f"Warning running exiftool: {exif_warn}", fg="yellow")
                if exif_error:
                    click.secho(f"Error running exiftool: {exif_error}", fg="red")

    if fp is not None:
        fp.close()

    click.echo(f"Done.")


def update_photo_date_time(photo, date, time, date_delta, time_delta):
    """Update date, time in photo"""
    photo_date = photo.date
    new_photo_date = update_datetime(
        photo_date, date=date, time=time, date_delta=date_delta, time_delta=time_delta
    )
    if new_photo_date != photo_date:
        photo.date = new_photo_date
        verbose(
            f"Updated date/time for photo {photo.filename} ({photo.uuid}) from: {photo_date} to {new_photo_date}"
        )
    else:
        verbose(
            f"Skipped date/time update for photo {photo.filename} ({photo.uuid}): nothing to do"
        )


def pluralize(count, singular, plural):
    """Return singular or plural based on count"""
    if count == 1:
        return singular
    else:
        return plural


# def rich_text(text, width=78):
#     """Return rich formatted text"""
#     sio = io.StringIO()
#     console = Console(file=sio, force_terminal=True, width=width)
#     console.print(text)
#     rich_text = sio.getvalue()
#     sio.close()
#     return rich_text


# def strip_md_header_and_links(md):
#     """strip markdown headers and links from markdown text md

#     Args:
#         md: str, markdown text

#     Returns:
#         str with markdown headers and links removed

#     Note: This uses a very basic regex that likely fails on all sorts of edge cases
#     but works for the links in the osxphotos docs
#     """
#     links = r"(?:[*#])|\[(.*?)\]\(.+?\)"

#     def subfn(match):
#         return match.group(1)

#     return re.sub(links, subfn, md)


# def strip_md_links(md):
#     """strip markdown links from markdown text md

#     Args:
#         md: str, markdown text

#     Returns:
#         str with markdown links removed

#     Note: This uses a very basic regex that likely fails on all sorts of edge cases
#     but works for the links in the osxphotos docs
#     """
#     links = r"\[(.*?)\]\(.+?\)"

#     def subfn(match):
#         return match.group(1)

#     return re.sub(links, subfn, md)


# def strip_html_comments(text):
#     """Strip html comments from text (which doesn't need to be valid HTML)"""
#     return re.sub(r"<!--(.|\s|\n)*?-->", "", text)


def main():
    cli()
