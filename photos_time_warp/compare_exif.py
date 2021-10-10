""" PhotoCompare class to compare date/time/timezone in Photos to the exif data """

from collections import namedtuple
from typing import Callable, List, Optional, Tuple

from osxphotos import PhotosDB
from osxphotos.exiftool import ExifTool
from photoscript import Photo

from .datetime_utils import datetime_naive_to_local, datetime_to_new_tz
from .exif_updater import get_exif_date_time_offset
from .phototz import PhotoTimeZone
from .utils import green, noop, red

ExifDiff = namedtuple(
    "ExifDiff",
    [
        "diff",
        "photos_date",
        "photos_time",
        "photos_tz",
        "exif_date",
        "exif_time",
        "exif_tz",
    ],
)


class PhotoCompare:
    """Class to compare date/time/timezone in Photos to the exif data"""

    def __init__(
        self,
        library_path: Optional[str] = None,
        verbose: Optional[Callable] = None,
        exiftool_path: Optional[str] = None,
    ):
        self.library_path = library_path
        self.db = PhotosDB(self.library_path)
        self.verbose = verbose or noop
        self.exiftool_path = exiftool_path
        self.phototz = PhotoTimeZone(self.library_path)

    def compare_exif(self, photo: Photo) -> List[str]:
        """Compare date/time/timezone in Photos to the exif data

        Args:
            photo (Photo): Photo object to compare

        Returns:
            List of strings:
        """
        photos_offset_seconds, photos_tz_str, _ = self.phototz.get_timezone(photo)
        photos_date = datetime_naive_to_local(photo.date)
        photos_date = datetime_to_new_tz(photos_date, photos_offset_seconds)
        photos_date_str = photos_date.strftime("%Y-%m-%d %H:%M:%S")

        photo_ = self.db.get_photo(photo.uuid)
        photo_path = photo_.path
        if photo_path:
            exif = ExifTool(filepath=photo_path, exiftool=self.exiftool_path)
            exif_dict = exif.asdict()
            exif_dt_offset = get_exif_date_time_offset(exif_dict)
            exif_offset = exif_dt_offset.offset_str
            exif_date = (
                exif_dt_offset.datetime.strftime("%Y-%m-%d %H:%M:%S")
                if exif_dt_offset.datetime
                else ""
            )
        else:
            exif_date = ""
            exif_offset = ""

        return [photos_date_str, photos_tz_str, exif_date, exif_offset]

    def compare_exif_with_markup(self, photo: Photo) -> ExifDiff:
        """Compare date/time/timezone in Photos to the exif data and return an ExifDiff named tuple;
        adds rich markup to strings to show differences

        Args:
            photo (Photo): Photo object to compare
        """
        photos_date, photos_tz, exif_date, exif_tz = self.compare_exif(photo)
        diff = False
        photos_date, photos_time = photos_date.split(" ", 1)
        try:
            exif_date, exif_time = exif_date.split(" ", 1)
        except ValueError:
            exif_date = exif_date
            exif_time = ""

        if photos_date != exif_date:
            photos_date = red(photos_date)
            exif_date = red(exif_date)
            diff = True
        else:
            photos_date = green(photos_date)
            exif_date = green(exif_date)

        if photos_time != exif_time:
            photos_time = red(photos_time)
            exif_time = red(exif_time)
            diff = True
        else:
            photos_time = green(photos_time)
            exif_time = green(exif_time)

        if photos_tz != exif_tz:
            photos_tz = red(photos_tz)
            exif_tz = red(exif_tz)
            diff = True
        else:
            photos_tz = green(photos_tz)
            exif_tz = green(exif_tz)

        return ExifDiff(
            diff,
            photos_date,
            photos_time,
            photos_tz,
            exif_date,
            exif_time,
            exif_tz,
        )
