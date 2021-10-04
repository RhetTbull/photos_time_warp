""" PhotoCompare class to compare date/time/timezone in Photos to the exif data """

from typing import Callable, List, Optional

from osxphotos import PhotosDB
from osxphotos.exiftool import ExifTool
from photoscript import Photo

from .datetime_utils import datetime_naive_to_local, datetime_to_new_tz
from .phototz import PhotoTimeZone


def noop():
    """No-op function for use as verbose if verbose not set"""
    pass


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
            exif_dict = exif.asdict(tag_groups=False)
            exif_date = exif_dict.get("DateTimeOriginal", "")
            exif_date, exif_time = exif_date.split(" ", 1)
            exif_date = exif_date.replace(":", "-")
            exif_date = exif_date + " " + exif_time
            exif_offset = exif_dict.get("OffsetTimeOriginal", "")
            exif_offset = exif_offset.replace(":", "")
        else:
            exif_date = ""
            exif_offset = ""

        return [photos_date_str, photos_tz_str, exif_date, exif_offset]
