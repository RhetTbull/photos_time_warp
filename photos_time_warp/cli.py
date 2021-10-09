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
from rich.highlighter import NullHighlighter
from rich.traceback import install

from ._version import __version__
from .compare_exif import ExifDiff, PhotoCompare
from .datetime_utils import datetime_naive_to_local, datetime_to_new_tz
from .exif_updater import ExifUpdater
from .photosalbum import PhotosAlbum
from .phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from .timeutils import (
    time_string_to_datetime,
    update_datetime,
    utc_offset_string_to_seconds,
)
from .timezones import Timezone
from .utils import green, pluralize, red

# name of the script
APP_NAME = "photos_time_warp"

# Set up rich console
_console = Console()
_console_stderr = Console(stderr=True)

# if True, shows verbose output, controlled via --verbose flag
_verbose = False

# format for pretty printing date/times
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"


def verbose(message_str, **kwargs):
    if not _verbose:
        return
    _console.print(message_str, **kwargs)


def print_help_msg(command):
    with Context(command) as ctx:
        click.echo(command.get_help(ctx))


def print_error(message):
    """Print error message to stderr with rich"""
    _console_stderr.print(message, style="bold red")


def print_warning(message):
    """Print warning message to stdout with rich"""
    _console.print(message, style="bold yellow")


def echo(message):
    """print to stdout using rich"""
    _console.print(message)


requires_one = RequireExactly(1).rephrased(
    help="requires one",
    error=f"it must be used with:\n" f"{ErrorFmt.param_list}",
)


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
    "Specify one or more command",
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
        help="Compare the EXIF date/time/timezone for each selected photo to the same data in Photos. "
        "Requires the third-party exiftool utility be installed (see https://exiftool.org/). "
        "See also --add-to-album.",
    ),
    option(
        "--push-exif",
        "-p",
        is_flag=True,
        help="Push date/time and timezone for selected photos from Photos to the "
        "EXIF metadata in the original file in the Photos library. "
        "Requires the third-party exiftool utility be installed (see https://exiftool.org/). "
        "Using this option modifies the *original* file of the image in your Photos library. "
        "--push-exif will be executed after any other updates are performed on the photo. "
        "See also --pull-exif.",
    ),
    option(
        "--pull-exif",
        "-P",
        is_flag=True,
        help="Pull date/time and timezone for selected photos from EXIF metadata in the original file "
        "into Photos and update the associated data in Photos to match the EXIF data. "
        "--pull-exif will be executed before any other updates are performed on the photo. "
        "It is possible for images to have missing EXIF data, for example the date/time could be set but there might be "
        "no timezone set in the EXIF metadata. "
        "Missing data will be handled thusly: if date/time/timezone are all present in the EXIF data, "
        "the photo's date/time/timezone will be updated. If timezone is missing but date/time is present, "
        "only the photo's date/time will be updated.  If date/time is missing but the timezone is present, only the "
        "photo's timezone will be updated. If the date is present but the time is missing, the time will be set to 00:00:00. "
        "Requires the third-party exiftool utility be installed (see https://exiftool.org/). "
        "See also --push-exif.",
    ),
    constraint=RequireAtLeast(1),
)
@constraint(mutually_exclusive, ["date", "date_delta"])
@constraint(mutually_exclusive, ["time", "time_delta"])
@option_group(
    "Options",
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
    option(
        "--add-to-album",
        "-a",
        metavar="ALBUM",
        help="When used with --compare-exif, adds any photos with date/time/timezone differences "
        "between Photos/EXIF to album ALBUM.  If ALBUM does not exist, it will be created.",
    ),
    option("--verbose", "-V", "verbose_", is_flag=True, help="Show verbose output."),
    option(
        "--library",
        "-L",
        metavar="PHOTOS_LIBRARY_PATH",
        type=click.Path(),
        help=r"Path to Photos library (e.g. '~/Pictures/Photos\ Library.photoslibrary'). "
        f"This is not likely needed as {APP_NAME} will usually be able to locate the path to the open Photos library. "
        "Use --library only if you get an error that the Photos library cannot be located.",
    ),
    option(
        "--exiftool-path",
        "-e",
        type=click.Path(exists=True),
        help="Optional path to exiftool executable (will look in $PATH if not specified) for those options which require exiftool.",
    ),
    option(
        "--plain",
        is_flag=True,
        help="Plain text mode.  Do not use rich output.",
        hidden=True,
    ),
)
@constraint(If("match_time", then=requires_one), ["timezone"])
@constraint(If("add_to_album", then=requires_one), ["compare_exif"])
@version_option(version=__version__)
def cli(
    date,
    date_delta,
    time,
    time_delta,
    timezone,
    inspect,
    compare_exif,
    push_exif,
    pull_exif,
    match_time,
    add_to_album,
    exiftool_path,
    verbose_,
    library,
    plain,
):
    """photos_time_warp: adjust date/time/timezone of photos in Apple Photos.
    Changes will be applied to all photos currently selected in Photos.
    photos_time_warp cannot operate on photos selected in a Smart Album;
    select photos in a regular album or in the 'All Photos' view.
    """

    # install rich traceback output
    install(show_locals=True)

    # used to control whether to print out verbose output
    global _verbose
    _verbose = verbose_

    if any([compare_exif, push_exif, pull_exif]):
        exiftool_path = exiftool_path or get_exiftool_path()
        verbose(f"exiftool path: {exiftool_path}")

    if plain:
        # Plain text mode, disable rich output (used for testing)
        global _console
        global _console_stderr
        _console = Console(highlighter=NullHighlighter())
        _console_stderr = Console(stderr=True, highlighter=NullHighlighter())

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
        album = PhotosAlbum(add_to_album) if add_to_album else None
        different_photos = 0
        if photos:
            photocomp = PhotoCompare(
                library_path=library, verbose=verbose, exiftool_path=exiftool_path
            )
            if not album:
                echo(
                    "filename, uuid, photo time (Photos), photo time (EXIF), timezone offset (Photos), timezone offset (EXIF)"
                )
        for photo in photos:
            diff_results = photocomp.compare_exif_with_markup(photo)
            filename = (
                red(photo.filename) if diff_results.diff else green(photo.filename)
            )
            if album:
                if diff_results.diff:
                    different_photos += 1
                    verbose(
                        f"Photo {filename} ({photo.uuid}) has different date/time/timezone, adding to album '{album.name}'"
                    )
                    album.add(photo)
                else:
                    verbose(
                        f"Photo {filename} ({photo.uuid}) has same date/time/timezone"
                    )
            else:
                echo(
                    f"{filename}, {photo.uuid}, "
                    f"{diff_results.photos_date} {diff_results.photos_time}, {diff_results.exif_date} {diff_results.exif_time}, "
                    f"{diff_results.photos_tz}, {diff_results.exif_tz}"
                )
        if album:
            echo(
                f"Compared {len(photos)} photos, found {different_photos} "
                f"that {pluralize(different_photos, 'is', 'are')} different and "
                f"added {pluralize(different_photos, 'it', 'them')} to album '{album.name}'."
            )
        sys.exit(0)

    if timezone:
        tz_updater = PhotoTimeZoneUpdater(
            timezone, verbose=verbose, library_path=library
        )

    if any([push_exif, pull_exif]):
        exif_updater = ExifUpdater(
            library_path=library, verbose=verbose, exiftool_path=exiftool_path
        )

    echo(f"Processing {len(photos)} {pluralize(len(photos), 'photo', 'photos')}")
    # send progress bar output to /dev/null if verbose to hide the progress bar
    fp = open(os.devnull, "w") if _verbose else None
    with click.progressbar(photos, file=fp) as bar:
        for p in bar:
            if pull_exif:
                exif_updater.update_photos_from_exif(p)
            if any([date, time, date_delta, time_delta]):
                update_photo_date_time_(p)
            if match_time:
                # need to adjust time before the timezone is updated
                # or the old timezone will be overwritten in the database
                update_photo_time_for_new_timezone_(photo=p, new_timezone=timezone)
            if timezone:
                tz_updater.update_photo(p)
            if push_exif:
                # this should be the last step in the if chain to ensure all Photos data is updated
                # before exiftool is run
                exif_warn, exif_error = exif_updater.update_exif_from_photos(p)
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


def main():
    cli()
