""" Tests which require user interaction to run """

import os
import time

import pytest
from click.testing import CliRunner
from osxphotos import PhotosDB
from osxphotos.exiftool import ExifTool

from tests.parse_output import parse_compare_exif, parse_inspect_output
from tests.conftest import (
    copy_photos_library,
    get_os_version,
    photoslib,
    suspend_capture,
)

# set timezone to avoid issues with comparing dates
os.environ["TZ"] = "US/Pacific"
time.tzset()

OS_VER = get_os_version()[1]
if OS_VER == "15":
    from tests.config_catalina import CATALINA_PHOTOS_5 as TEST_DATA

else:
    pytest.exit("This test suite currently only runs on MacOS Catalina ")


def say(msg: str) -> None:
    """Say message with text to speech"""
    os.system(f"say {msg}")


########## Interactive tests run first ##########


def test_inspect(photoslib, suspend_capture):
    """Test --inspect. NOTE: this test requires user interaction"""
    from photos_time_warp.cli import cli

    with suspend_capture:
        prompt = "Select the photo of the pears then press Enter."
        say(prompt)
        input(f"\n{prompt}")

    runner = CliRunner()
    result = runner.invoke(cli, ["--inspect", "--plain"])
    assert result.exit_code == 0
    output = result.output
    values = parse_inspect_output(output)
    assert TEST_DATA["inspect"]["expected"] == values


def test_date(photoslib, suspend_capture):
    """Test --date"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--date",
            TEST_DATA["date"]["value"],
            "--plain",
        ],
    )
    assert result.exit_code == 0
    photo = photoslib.selection[0]
    assert photo.date == TEST_DATA["date"]["date"]


@pytest.mark.parametrize("input_value,expected", TEST_DATA["date_delta"]["parameters"])
def test_date_delta(photoslib, suspend_capture, input_value, expected):
    """Test --date-delta"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--date-delta",
            input_value,
            "--plain",
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--inspect", "--plain"])
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["time"]["parameters"])
def test_time(photoslib, suspend_capture, input_value, expected):
    """Test --time"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--time",
            input_value,
            "--plain",
        ],
    )
    assert result.exit_code == 0
    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(cli, ["--inspect", "--plain"])
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["time_delta"]["parameters"])
def test_time_delta(photoslib, suspend_capture, input_value, expected):
    """Test --time-delta"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--time-delta",
            input_value,
            "--plain",
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--inspect", "--plain"])
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize(
    "input_value,expected_date,expected_tz", TEST_DATA["time_zone"]["parameters"]
)
def test_time_zone(photoslib, suspend_capture, input_value, expected_date, expected_tz):
    """Test --time-zone"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--timezone",
            input_value,
            "--plain",
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--inspect", "--plain"])
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected_date
    assert output_values[0].tz_offset == expected_tz


@pytest.mark.parametrize("expected", TEST_DATA["compare_exif"]["expected"])
def test_compare_exif(photoslib, suspend_capture, expected):
    """Test --compare-exif"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--compare-exif",
            "--plain",
        ],
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == expected


@pytest.mark.parametrize(
    "expected,album", TEST_DATA["compare_exif_add_to_album"]["expected"]
)
def test_compare_exif_add_to_album(photoslib, suspend_capture, expected, album):
    """Test --compare-exif --add-to-album"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--compare-exif",
            "--add-to-album",
            album,
            "--plain",
        ],
    )
    assert result.exit_code == 0
    assert expected in result.output
    photo = photoslib.selection[0]
    assert album in [album.name for album in photo.albums]


@pytest.mark.parametrize("expected", TEST_DATA["compare_exif_3"]["expected"])
def test_compare_exif_3(photoslib, suspend_capture, expected):
    """Test --compare-exif"""
    from photos_time_warp.cli import cli

    with suspend_capture:
        prompt = "Select the photo of the sunflowers then press Enter."
        say(prompt)
        input(f"\n{prompt}")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--compare-exif",
            "--plain",
        ],
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["match"]["parameters"])
def test_match(photoslib, suspend_capture, input_value, expected):
    """Test --timezone --match"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--timezone",
            input_value,
            "--match-time",
            "--plain",
        ],
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--inspect", "--plain"])
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize(
    "match,tz_value,time_delta_value,expected_date,exif_date,exif_offset",
    TEST_DATA["exiftool"]["parameters"],
)
def test_exiftool(
    photoslib,
    suspend_capture,
    match,
    tz_value,
    time_delta_value,
    expected_date,
    exif_date,
    exif_offset,
):
    """Test --timezone --match"""
    from photos_time_warp.cli import cli

    with suspend_capture:
        prompt = "Select the photo of the pumpkins then press Enter."
        say(prompt)
        input(f"\n{prompt}")

    cli_args = [
        "--timezone",
        tz_value,
        "--time-delta",
        time_delta_value,
        "--exiftool",
        "--plain",
    ]
    if match:
        cli_args.append("--match-time")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        cli_args,
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--inspect", "--plain"])
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected_date

    photo = photoslib.selection[0]
    uuid = photo.uuid
    path = PhotosDB().get_photo(uuid).path
    exif = ExifTool(path)
    exifdict = exif.asdict()
    assert exifdict["EXIF:DateTimeOriginal"] == exif_date
    assert exifdict["EXIF:OffsetTimeOriginal"] == exif_offset
