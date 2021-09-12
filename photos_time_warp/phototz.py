""" Update the timezone of a photo in Apple Photos' library """
# WARNING: This is a hack.  It might destroy your Photos library.
# Ensure you have a backup before using!
# You have been warned.

import pathlib
import plistlib
import sys
from typing import Optional

from osxphotos._constants import (
    _DB_TABLE_NAMES,
    _PHOTOS_5_MODEL_VERSION,
    _PHOTOS_6_MODEL_VERSION,
    _PHOTOS_7_MODEL_VERSION,
)
from osxphotos.utils import get_last_library_path, get_system_library_path
from photoscript import Photo
from tenacity import retry, stop_after_attempt, wait_exponential

from .sqlite_native import execute, query
from .timezones import Timezone


def get_db_model_version(db_file):
    """Returns the database model version from Z_METADATA

    Args:
        db_file: path to Photos.sqlite database file containing Z_METADATA table

    Returns: model version as str
    """

    # get database version
    results = query(
        db_file, "SELECT MAX(Z_VERSION) AS Z_VERSION, Z_PLIST FROM Z_METADATA"
    )
    row = next(results)
    plist = plistlib.loads(row.Z_PLIST)
    return plist["PLModelVersion"]


def get_photos_version(db_file):
    """Returns Photos version based on model version found in db_file

    Args:
        db_file: path to Photos.sqlite file

    Returns: int of major Photos version number (e.g. 5 or 6).
    If unknown model version found, logs warning and returns most current Photos version.
    """

    model_ver = get_db_model_version(db_file)
    if _PHOTOS_5_MODEL_VERSION[0] <= model_ver <= _PHOTOS_5_MODEL_VERSION[1]:
        return 5
    elif _PHOTOS_6_MODEL_VERSION[0] <= model_ver <= _PHOTOS_6_MODEL_VERSION[1]:
        return 6
    elif _PHOTOS_7_MODEL_VERSION[0] <= model_ver <= _PHOTOS_7_MODEL_VERSION[1]:
        return 7
    else:
        # cross our fingers and try latest version
        return 7


def noop():
    """No-op function for use as verbose if verbose not set"""
    pass


class PhotoTimeZoneUpdater:
    """Update timezones for Photos objects"""

    def __init__(
        self,
        timezone: Timezone,
        verbose: Optional[callable] = None,
        library_path: Optional[str] = None,
    ):
        self.timezone = timezone
        self.tz_offset = timezone.offset
        self.tz_name = timezone.name

        self.verbose = verbose or noop

        # get_last_library_path() returns the path to the last Photos library
        # opened but sometimes (rarely) fails on some systems
        try:
            db_path = (
                library_path or get_last_library_path() or get_system_library_path()
            )
        except Exception:
            db_path = None
        if not db_path:
            raise FileNotFoundError("Could not find Photos database path")

        db_path = str(pathlib.Path(db_path) / "database/Photos.sqlite")
        self.db_path = db_path
        photos_version = get_photos_version(self.db_path)
        self.ASSET_TABLE = _DB_TABLE_NAMES[photos_version]["ASSET"]

    def update_photo(self, photo: Photo):
        """Update the timezone of a photo in the database

        Args:
            photo: Photo object to update
        """
        try:
            self._update_photo(photo)
        except Exception as e:
            self.verbose(f"Error updating {photo.uuid}: {e}")

    @retry(
        wait=wait_exponential(multiplier=1, min=0.100, max=5),
        stop=stop_after_attempt(10),
    )
    def _update_photo(self, photo: Photo):
        try:
            uuid = photo.uuid
            sql = f"""  SELECT 
                        ZADDITIONALASSETATTRIBUTES.Z_PK, 
                        ZADDITIONALASSETATTRIBUTES.Z_OPT, 
                        ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, 
                        ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME
                        FROM ZADDITIONALASSETATTRIBUTES
                        JOIN {self.ASSET_TABLE} 
                        ON ZADDITIONALASSETATTRIBUTES.ZASSET = {self.ASSET_TABLE}.Z_PK
                        WHERE {self.ASSET_TABLE}.ZUUID = '{uuid}' 
                """
            results = query(self.db_path, sql)
            row = next(results)
            z_opt = row.Z_OPT + 1
            z_pk = row.Z_PK
            sql_update = f"""   UPDATE ZADDITIONALASSETATTRIBUTES
                                SET Z_OPT={z_opt}, 
                                ZTIMEZONEOFFSET={self.tz_offset}, 
                                ZTIMEZONENAME='{self.tz_name}' 
                                WHERE Z_PK={z_pk};
                        """
            results = execute(self.db_path, sql_update)
            self.verbose(
                f"Updated timezone for photo {photo.filename} ({photo.uuid}) "
                + f"from {row.ZTIMEZONENAME}, offset={row.ZTIMEZONEOFFSET} "
                + f"to {self.tz_name}, offset={self.tz_offset}"
            )
        except Exception as e:
            raise e
