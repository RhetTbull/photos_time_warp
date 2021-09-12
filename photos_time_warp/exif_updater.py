"""Use exiftool to update exif data in photos """

import datetime
from typing import Optional, Tuple

from osxphotos import PhotosDB
from osxphotos.datetime_utils import datetime_tz_to_utc
from osxphotos.exiftool import ExifTool
from photoscript import Photo

from .timezones import Timezone


def noop():
    """No-op function for use as verbose if verbose not set"""
    pass


def format_offset_time(offset: int) -> str:
    """Format offset time to exiftool format: -04:00"""
    sign = "-" if offset < 0 else "+"
    hours, remainder = divmod(abs(offset), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


class ExifUpdater:
    """Update exif data in photos"""

    def __init__(
        self,
        library_path: Optional[str] = None,
        verbose: Optional[callable] = None,
        exiftool_path: Optional[str] = None,
    ):
        self.library_path = library_path
        self.db = PhotosDB(self.library_path)
        self.verbose = verbose or noop
        self.exiftool_path = exiftool_path

    def update_photo(
        self,
        photo: Photo,
        timezone_offset: Optional[Timezone] = None,
    ) -> Tuple[str, str]:
        """Update exif data in photo"""

        # photo is the photoscript.Photo object passed in
        # _photo is the osxphotos.PhotoInfo object for the same photo
        # Need _photo to get the photo's path
        _photo = self.db.get_photo(photo.uuid)
        if not _photo:
            raise ValueError(f"Photo {photo.uuid} not found")

        if not _photo.path:
            self.verbose(
                f"Skipping exiftool update for missing photo {_photo.original_filename} ({_photo.uuid})"
            )
            return "", ""

        self.verbose(f"Updating EXIF data for {photo.filename} ({photo.uuid})")

        photo_date = photo.date

        if timezone_offset:
            offset = format_offset_time(timezone_offset.offset)
        else:
            offset = format_offset_time(_photo._info["imageTimeZoneOffsetSeconds"])

        # # exiftool expects format to "2015:01:18 12:00:00"
        datetimeoriginal = photo_date.strftime("%Y:%m:%d %H:%M:%S")

        # process date/time and timezone offset
        # Photos exports the following fields and sets modify date to creation date
        # [EXIF]    Date/Time Original      : 2020:10:30 00:00:00
        # [EXIF]    Create Date             : 2020:10:30 00:00:00
        # [IPTC]    Digital Creation Date   : 2020:10:30
        # [IPTC]    Date Created            : 2020:10:30
        #
        # for videos:
        # [QuickTime]     CreateDate                      : 2020:12:11 06:10:10
        # [Keys]          CreationDate                    : 2020:12:10 22:10:10-08:00
        exif = {}
        if _photo.isphoto:
            exif["EXIF:DateTimeOriginal"] = datetimeoriginal
            exif["EXIF:CreateDate"] = datetimeoriginal
            exif["EXIF:OffsetTimeOriginal"] = offset

            dateoriginal = photo_date.strftime("%Y:%m:%d")
            exif["IPTC:DateCreated"] = dateoriginal

            timeoriginal = photo_date.strftime(f"%H:%M:%S{offset}")
            exif["IPTC:TimeCreated"] = timeoriginal
        elif _photo.ismovie:
            # QuickTime spec specifies times in UTC
            # QuickTime:CreateDate and ModifyDate are in UTC w/ no timezone
            # QuickTime:CreationDate must include time offset or Photos shows invalid values
            # reference: https://exiftool.org/TagNames/QuickTime.html#Keys
            #            https://exiftool.org/forum/index.php?topic=11927.msg64369#msg64369
            creationdate = f"{datetimeoriginal}{offset}"
            exif["QuickTime:CreationDate"] = creationdate

            # need to convert to UTC then back to formatted string
            tzdate = datetime.datetime.strptime(creationdate, "%Y:%m:%d %H:%M:%S%z")
            utcdate = datetime_tz_to_utc(tzdate)
            createdate = utcdate.strftime("%Y:%m:%d %H:%M:%S")
            exif["QuickTime:CreateDate"] = createdate

        self.verbose(f"Writing EXIF data with exiftool to {_photo.path}")
        with ExifTool(filepath=_photo.path, exiftool=self.exiftool_path) as exiftool:
            for tag, val in exif.items():
                if type(val) == list:
                    for v in val:
                        exiftool.setvalue(tag, v)
                else:
                    exiftool.setvalue(tag, val)
        return exiftool.warning, exiftool.error
