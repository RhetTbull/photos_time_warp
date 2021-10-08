""" Test data for Catalina/Photos 5 """

import datetime

from tests.parse_output import CompareValues, InspectValues

TEST_LIBRARY = "TestTimeWarp-10.15.7.photoslibrary"

CATALINA_PHOTOS_5 = {
    "inspect": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": [
            InspectValues(
                "IMG_6501.jpeg",
                "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
                "2021-10-02 12:40:07-0700",
                "2021-10-02 12:40:07-0700",
                "-0700",
                "GMT-0700",
            )
        ],
    },
    "date": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "value": "2020-09-01",
        "date": datetime.datetime(2020, 9, 1, 12, 40, 7),
    },
    "date_delta": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("1", "2020-09-02 12:40:07-0700"),
            ("1 day", "2020-09-03 12:40:07-0700"),
            ("1 week", "2020-09-10 12:40:07-0700"),
            ("-1", "2020-09-09 12:40:07-0700"),
            ("-1 day", "2020-09-08 12:40:07-0700"),
            ("-1 week", "2020-09-01 12:40:07-0700"),
        ],
    },
    "time": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("14:42", "2020-09-01 14:42:00-0700"),
            ("14:42:30", "2020-09-01 14:42:30-0700"),
            # Photos doesn't return the milliseconds
            ("14:42:31.234", "2020-09-01 14:42:31-0700"),
        ],
    },
    "time_delta": {
        # IMG_6501.jpeg
        # Format is one of '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or min), '±S seconds' (or sec), '±S'(where S is seconds)
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("1:10:20", "2020-09-01 15:52:51-0700"),
            ("1 hours", "2020-09-01 16:52:51-0700"),
            ("1", "2020-09-01 16:52:52-0700"),
            ("+1", "2020-09-01 16:52:53-0700"),
            ("-1", "2020-09-01 16:52:52-0700"),
            ("-1 hour", "2020-09-01 15:52:52-0700"),
            ("3 minutes", "2020-09-01 15:55:52-0700"),
            ("3 min", "2020-09-01 15:58:52-0700"),
            ("-6 min", "2020-09-01 15:52:52-0700"),
            ("+10 sec", "2020-09-01 15:53:02-0700"),
        ],
    },
    "time_zone": {
        # IMG_6501.jpeg
        # Format is one of '±HH:MM', '±H:MM', or '±HHMM'
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "parameters": [
            ("-06:00", "2020-09-01 16:53:02-0600", "-0600"),
        ],
    },
    "compare_exif": {
        # IMG_6501.jpeg
        # filename, uuid, photo time (Photos), photo time (EXIF), timezone offset (Photos), timezone offset (EXIF)
        # IMG_6501.jpeg, 2F00448D-3C0D-477A-9B10-5F21DCAB405A, 2020-09-01 16:53:02, 2021-10-02 12:40:07, -0600, -0700
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": [
            CompareValues(
                "IMG_6501.jpeg",
                "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
                "2020-09-01 16:53:02",
                "2021-10-02 12:40:07",
                "-0600",
                "-0700",
            ),
        ],
    },
    "compare_exif_add_to_album": {
        # IMG_6501.jpeg
        "uuid": "2F00448D-3C0D-477A-9B10-5F21DCAB405A",
        "expected": [("found 1 that is different", "Different EXIF")],
    },
    "compare_exif_3": {
        # IMG_6520.jpeg
        # IMG_6520.jpeg, 53615D56-91F7-4908-81F1-B93B5DEA7449, 2021-10-02 12:54:36,  , -0700,
        "uuid": "53615D56-91F7-4908-81F1-B93B5DEA7449",
        "expected": [
            CompareValues(
                "IMG_6520.jpeg",
                "53615D56-91F7-4908-81F1-B93B5DEA7449",
                "2021-10-02 12:54:36",
                "",
                "-0700",
                "",
            ),
        ],
    },
    "match": {  # IMG_6520.jpeg
        # IMG_6520.jpeg, 53615D56-91F7-4908-81F1-B93B5DEA7449, 2021-10-02 12:54:36,  , -0700,
        "uuid": "53615D56-91F7-4908-81F1-B93B5DEA7449",
        "parameters": [
            ("-0500", "2021-10-02 12:54:36-0500"),
            ("+01:00", "2021-10-02 12:54:36+0100"),
        ],
    },
    "exiftool": {
        # IMG_6522.jpeg
        "uuid": "FD1E3A36-3E65-48AF-9B14-DCFF65A9D3D2",
        # match,tz_value,time_delta_value,expected_date,exif_date,exif_offset
        "parameters": [
            (
                True,
                "-0300",
                "+1 hour",
                "2021-10-02 13:56:11-0300",
                "2021:10:02 13:56:11",
                "-03:00",
            ),
            (
                False,
                "-0400",
                "+2 hours",
                "2021-10-02 14:56:11-0400",
                "2021:10:02 14:56:11",
                "-04:00",
            ),
        ],
    },
}
