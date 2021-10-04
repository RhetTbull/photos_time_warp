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
from cloup.constraints import (
    ErrorFmt,
    If,
    RequireAtLeast,
    RequireExactly,
    mutually_exclusive,
)
from osxphotos.exiftool import get_exiftool_path
from photoscript import Photo, PhotosLibrary
from rich.console import Console

from ._version import __version__
from .compare_exif import PhotoCompare, ExifDiff
from .datetime_utils import datetime_naive_to_local, datetime_to_new_tz
from .exif_updater import ExifUpdater
from .phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from .timeutils import (
    time_string_to_datetime,
    update_datetime,
    utc_offset_string_to_seconds,
)
from .timezones import Timezone

# name of the script
APP_NAME = "photos_time_warp"

# Set up rich console
CONSOLE = Console()
CONSOLE_STDERR = Console(stderr=True)

# if True, shows verbose output, controlled via --verbose flag
VERBOSE = False

# format for pretty printing date/times
DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S%z"


def verbose(message_str, **kwargs):
    if not VERBOSE:
        return
    CONSOLE.print(message_str, **kwargs)


def print_help_msg(command):
    with Context(command) as ctx:
        click.echo(command.get_help(ctx))


def print_error(message):
    """Print error message to stderr with rich"""
    CONSOLE_STDERR.print(message, style="bold red")


def print_warning(message):
    """Print warning message to stdout with rich"""
    CONSOLE.print(message, style="bold yellow")


def echo(message):
    """print to stdout using rich"""
    CONSOLE.print(message)


requires_one = RequireExactly(1).rephrased(
    help="requires one",
    error=f"it must be used with:\n" f"{ErrorFmt.param_list}",
)


def red(msg: str) -> str:
    """Return red string in rich markdown"""
    return f"[red]{msg}[/red]"


def green(msg: str) -> str:
    """Return green string in rich markdown"""
    return f"[green]{msg}[/green]"


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
        "-d",
        metavar="DATE",
        type=DateTimeISO8601(),
        help="Set date for selected photos. Format is 'YYYY-MM-DD'.",
    ),
    option(
        "--date-delta",
        "-D",
        metavar="DELTA",
        type=DateOffset(),
        help="Adjust date for selected photos by DELTA. "
        "Format is one of: '±D days', '±W weeks', '±D' where D is days",
    ),
    option(
        "--time",
        "-t",
        metavar="TIME",
        type=TimeString(),
        help="Set time for selected photos. Format is one of 'HH:MM:SS', 'HH:MM:SS.fff', 'HH:MM'.",
    ),
    option(
        "--time-delta",
        "-T",
        metavar="DELTA",
        type=TimeOffset(),
        help="Adjust time for selected photos by DELTA time. "
        "Format is one of '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or min), '±S seconds' (or sec), '±S' (where S is seconds)",
    ),
    option(
        "--timezone",
        "-z",
        metavar="TIMEZONE",
        type=UTCOffset(),
        help="Set timezone for selected photos as offset from UTC. "
        "Format is one of '±HH:MM', '±H:MM', or '±HHMM'. "
        "The actual time of the photo is not adjusted which means, somewhat counterintuitively, "
        "that the time in the new timezone will be different. "
        "For example, if photo has time of 12:00 and timezone of GMT+01:00 and new timezone is specified as "
        "'--timezone +02:00' (one hour ahead of current GMT+01:00 timezone), the photo's new time will be 13:00 GMT+02:00, "
        "which is equivalent to the old time of 12:00+01:00. "
        "This is the same behavior exhibited by Photos when manually adjusting timezone in the Get Info window. "
        "See also --match-time. ",
    ),
    option(
        "--inspect",
        "-i",
        is_flag=True,
        help="Print out the date/time/timezone for each selected photo without changing any information.",
    ),
    option(
        "--compare-exif",
        "-c",
        is_flag=True,
        help="Compare the EXIF date/time/timezone for each selected photo to the same data in Photos.",
    ),
    constraint=RequireAtLeast(1),
)
@constraint(mutually_exclusive, ["date", "date_delta"])
@constraint(mutually_exclusive, ["time", "time_delta"])
@option_group(
    "Settings",
    option(
        "--match-time",
        "-m",
        is_flag=True,
        help="When used with --timezone, adjusts the photo time so that the timestamp in the new timezone matches "
        "the timestamp in the old timezone. "
        "For example, if photo has time of 12:00 and timezone of GMT+01:00 and new timezone is specified as "
        "'--timezone +02:00' (one hour ahead of current GMT+01:00 timezone), the photo's new time will be 12:00 GMT+02:00. "
        "That is, the timezone will have changed but the timestamp of the photo will match the previous timestamp. "
        "Use --match-time when the camera's time was correct for the time the photo was taken but the "
        "timezone was missing or wrong and you want to adjust the timezone while preserving the photo's time. "
        "See also --timezone.",
    ),
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
        "-x",
        is_flag=True,
        help="Use exiftool to also update the date/time/timezone metadata in the original file in Photos' library. "
        "To use --exiftool, you must have the third-party exiftool utility installed (see https://exiftool.org/). "
        "Using this option modifies the *original* file of the image in your Photos library. "
        "It is possible for originals to be missing from disk (for example, if they've not been downloaded from iCloud); "
        "--exiftool will skip those files which are missing.",
    ),
    option(
        "--exiftool-path",
        "-p",
        type=click.Path(exists=True),
        help="Optional path to exiftool executable (will look in $PATH if not specified).",
    ),
)
@constraint(If("match_time", then=requires_one), ["timezone"])
@version_option(version=__version__)
def cli(
    date,
    date_delta,
    time,
    time_delta,
    timezone,
    inspect,
    compare_exif,
    match_time,
    exiftool,
    exiftool_path,
    verbose_,
    library,
):
    """Adjust date/time/timezone of photos in Apple Photos.
    Changes will be applied to all photos currently selected in Photos.
    photos_time_warp cannot operate on photos selected in a Smart Album;
    select photos in a regular album or in the 'All Photos' view.
    """
    global VERBOSE
    VERBOSE = verbose_

    if exiftool:
        exiftool_path = exiftool_path or get_exiftool_path()
        verbose(f"exiftool path: {exiftool_path}")

    try:
        photos = PhotosLibrary().selection
        if not photos:
            print_warning("No photos selected")
            sys.exit(0)
    except Exception as e:
        # AppleScript error -1728 occurs if user attempts to get selected photos in a Smart Album
        if "(-1728)" in str(e):
            print_error(
                "Could not get selected photos. Ensure photos is open and photos are selected. "
                "If you have selected photos and you see this message, it may be because the selected photos are in a Photos Smart Album. "
                f"{APP_NAME} cannot access photos in a Smart Album.  Select the photos in a regular album or in 'All Photos' view. "
                "Another option is to create a new album using 'File | New Album With Selection' then select the photos in the new album.",
            )
        else:
            print_error(
                f"Could not get selected photos. Ensure Photos is open and photos to process are selected. {e}",
            )
        sys.exit(1)

    update_photo_date_time_ = partial(
        update_photo_date_time,
        date=date,
        time=time,
        date_delta=date_delta,
        time_delta=time_delta,
    )

    update_photo_time_for_new_timezone_ = partial(
        update_photo_time_for_new_timezone,
        library_path=library,
    )

    if inspect:
        tzinfo = PhotoTimeZone(library_path=library)
        if photos:
            print(
                "filename, uuid, photo time (local), photo time, timezone offset, timezone name"
            )
        for photo in photos:
            tz_seconds, tz_str, tz_name = tzinfo.get_timezone(photo)
            photo_date_local = datetime_naive_to_local(photo.date)
            photo_date_tz = datetime_to_new_tz(photo_date_local, tz_seconds)
            echo(
                f"{photo.filename}, {photo.uuid}, {photo_date_local.strftime(DATETIME_FORMAT)}, {photo_date_tz.strftime(DATETIME_FORMAT)}, {tz_str}, {tz_name}"
            )
        sys.exit(0)

    if compare_exif:
        if photos:
            photocomp = PhotoCompare(
                library_path=library, verbose=verbose, exiftool_path=exiftool_path
            )
            print(
                "filename, uuid, photo time (Photos), photo time (EXIF), timezone offset (Photos), timezone offset (EXIF)"
            )
        for photo in photos:
            diff_results = photocomp.compare_exif_with_markup(photo)
            filename = (
                red(photo.filename) if diff_results.diff else green(photo.filename)
            )
            echo(
                f"{filename}, {photo.uuid}, "
                f"{diff_results.photos_date} {diff_results.photos_time}, {diff_results.exif_date} {diff_results.exif_time}, "
                f"{diff_results.photos_tz}, {diff_results.exif_tz}"
            )
        sys.exit(0)

    if timezone:
        tz_updater = PhotoTimeZoneUpdater(
            timezone, verbose=verbose, library_path=library
        )

    if exiftool:
        exif_updater = ExifUpdater(
            library_path=library, verbose=verbose, exiftool_path=exiftool_path
        )

    echo(f"Processing {len(photos)} {pluralize(len(photos), 'photo', 'photos')}")
    # send progress bar output to /dev/null if verbose to hide the progress bar
    fp = open(os.devnull, "w") if VERBOSE else None
    with click.progressbar(photos, file=fp) as bar:
        for p in bar:
            if any([date, time, date_delta, time_delta]):
                update_photo_date_time_(p)
            if match_time:
                # need to adjust time before the timezone is updated
                # or the old timezone will be overwritten in the database
                update_photo_time_for_new_timezone_(photo=p, new_timezone=timezone)
            if timezone:
                tz_updater.update_photo(p)
            if exiftool:
                exif_warn, exif_error = exif_updater.update_photo(
                    p,
                    update_time=time or time_delta,  # ZZZ timezone?/match_time
                    update_date=date or date_delta,
                    timezone_offset=timezone,
                )
                if exif_warn:
                    print_warning(f"Warning running exiftool: {exif_warn}")
                if exif_error:
                    print_error(f"Error running exiftool: {exif_error}")

    if fp is not None:
        fp.close()

    echo("Done.")


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


def update_photo_time_for_new_timezone(
    library_path: str, photo: Photo, new_timezone: Timezone
):
    """Update time in photo to keep it the same time but in a new timezone

    For example, photo time is 12:00+0100 and new timezone is +0200,
    so adjust photo time by 1 hour so it will now be 12:00+0200 instead of
    13:00+0200 as it would be with no adjustment to the time"""
    old_timezone = PhotoTimeZone(library_path=library_path).get_timezone(photo)[0]
    # need to move time in opposite direction of timezone offset so that
    # photo time is the same time but in the new timezone
    delta = old_timezone - new_timezone.offset
    photo_date = photo.date
    new_photo_date = update_datetime(
        dt=photo_date, time_delta=datetime.timedelta(seconds=delta)
    )
    if photo_date != new_photo_date:
        photo.date = new_photo_date
        verbose(
            f"Adjusted date/time for photo {photo.filename} ({photo.uuid}) to match "
            f"previous time {photo_date} but in new timezone {new_timezone}."
        )
    else:
        verbose(
            f"Skipping date/time update for photo {photo.filename} ({photo.uuid}), already matches new timezone {new_timezone}"
        )


def pluralize(count, singular, plural):
    """Return singular or plural based on count"""
    if count == 1:
        return singular
    else:
        return plural


def main():
    cli()
