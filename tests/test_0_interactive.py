""" Tests which require user interaction to run """

import os
import time

import pytest
from click.testing import CliRunner
from osxphotos import PhotosDB
from osxphotos.exiftool import ExifTool

from tests.conftest import (
    copy_photos_library,
    get_os_version,
    photoslib,
    suspend_capture,
    output_file,
)
from tests.parse_output import parse_compare_exif, parse_inspect_output

# set timezone to avoid issues with comparing dates
os.environ["TZ"] = "US/Pacific"
time.tzset()

TERMINAL_WIDTH = 250

OS_VER = get_os_version()[1]
if OS_VER == "15":
    from tests.config_catalina import CATALINA_PHOTOS_5 as TEST_DATA

else:
    pytest.exit("This test suite currently only runs on MacOS Catalina ")


def say(msg: str) -> None:
    """Say message with text to speech"""
    os.system(f"say {msg}")


def ask_user_to_make_selection(
    photoslib, suspend_capture, photo_name: str, retry=3, video=False
) -> bool:
    """Ask user to make selection

    Args:
        photoslib: photoscript.PhotosLibrary instance passed from fixture
        suspend_capture: suspend capture fixture
        photo_name: name of the photo ask user for
        retry: number of times to retry before failing
        video: set to True if asking for a video instead of a photo
    """
    # needs to be called with a suspend_capture fixture
    photo_or_video = "photo" if not video else "video"
    tries = 0
    while tries < retry:
        with suspend_capture:
            prompt = f"Select the {photo_or_video} of the {photo_name} then press Enter in the Terminal."
            say(prompt)
            input(f"\n{prompt}")

        selection = photoslib.selection
        if (
            len(selection) == 1
            and selection[0].filename == TEST_DATA["filenames"][photo_name]
        ):
            return True
        tries += 1
    return False


########## Interactive tests run first ##########


def test_select_pears(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "pears")


def test_inspect(photoslib, suspend_capture, output_file):
    """Test --inspect. NOTE: this test requires user interaction"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    assert result.exit_code == 0
    values = parse_inspect_output(output_file)
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    photo = photoslib.selection[0]
    assert photo.date == TEST_DATA["date"]["date"]


@pytest.mark.parametrize("input_value,expected", TEST_DATA["date_delta"]["parameters"])
def test_date_delta(photoslib, suspend_capture, input_value, expected, output_file):
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["time"]["parameters"])
def test_time(photoslib, suspend_capture, input_value, expected, output_file):
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["time_delta"]["parameters"])
def test_time_delta(photoslib, suspend_capture, input_value, expected, output_file):
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize(
    "input_value,expected_date,expected_tz", TEST_DATA["time_zone"]["parameters"]
)
def test_time_zone(
    photoslib, suspend_capture, input_value, expected_date, expected_tz, output_file
):
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected_date
    assert output_values[0].tz_offset == expected_tz


@pytest.mark.parametrize("expected", TEST_DATA["compare_exif"]["expected"])
def test_compare_exif(photoslib, suspend_capture, expected, output_file):
    """Test --compare-exif"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--compare-exif",
            "--plain",
            "-o",
            output_file,
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(output_file)
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert expected in result.output
    photo = photoslib.selection[0]
    assert album in [album.name for album in photo.albums]


def test_select_sunflowers(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "sunflowers")


@pytest.mark.parametrize("expected", TEST_DATA["compare_exif_3"]["expected"])
def test_compare_exif_3(photoslib, suspend_capture, expected, output_file):
    """Test --compare-exif"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["match"]["parameters"])
def test_match(photoslib, suspend_capture, input_value, expected, output_file):
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


def test_push_exif_missing_file():
    """Test --push-exif when an original file is missing"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--push-exif", "--plain", "--verbose"], terminal_width=TERMINAL_WIDTH
    )
    assert result.exit_code == 0
    assert "Skipping EXIF update for missing photo" in result.output


def test_select_pumpkins(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "pumpkins")


@pytest.mark.parametrize(
    "match,tz_value,time_delta_value,expected_date,exif_date,exif_offset",
    TEST_DATA["exiftool"]["parameters"],
)
def test_push_exif_1(
    photoslib,
    match,
    tz_value,
    time_delta_value,
    expected_date,
    exif_date,
    exif_offset,
    output_file,
):
    """Test --timezone --match with --push-exif"""
    from photos_time_warp.cli import cli

    cli_args = [
        "--timezone",
        tz_value,
        "--time-delta",
        time_delta_value,
        "--push-exif",
        "--plain",
    ]
    if match:
        cli_args.append("--match-time")

    runner = CliRunner()
    result = runner.invoke(cli, cli_args, terminal_width=TERMINAL_WIDTH)
    assert result.exit_code == 0
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected_date

    photo = photoslib.selection[0]
    uuid = photo.uuid
    path = PhotosDB().get_photo(uuid).path
    exif = ExifTool(path)
    exifdict = exif.asdict()
    assert exifdict["EXIF:DateTimeOriginal"] == exif_date
    assert exifdict["EXIF:OffsetTimeOriginal"] == exif_offset


def test_select_pears_2(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "pears")


def test_push_exif_2(photoslib, suspend_capture, output_file):
    """Test --push-exif"""
    pre_test = TEST_DATA["push_exif"]["pre"]
    post_test = TEST_DATA["push_exif"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--push-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test


def test_pull_exif_1(photoslib, suspend_capture, output_file):
    """Test --pull-exif"""
    pre_test = TEST_DATA["pull_exif_1"]["pre"]
    post_test = TEST_DATA["pull_exif_1"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    # update the photo so we know if the data is updated
    result = runner.invoke(
        cli,
        ["-z", "-0400", "-D", "+1 day", "-m", "-V", "--plain"],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--pull-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test


def test_select_apple_tree(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "apple tree")


def test_pull_exif_no_time(photoslib, suspend_capture, output_file):
    """Test --pull-exif when photo has invalid date/time in EXIF"""
    pre_test = TEST_DATA["pull_exif_no_time"]["pre"]
    post_test = TEST_DATA["pull_exif_no_time"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--pull-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test


def test_select_marigolds(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "marigold flowers")


def test_pull_exif_no_offset(photoslib, suspend_capture, output_file):
    """Test --pull-exif when photo has no offset in EXIF"""
    pre_test = TEST_DATA["pull_exif_no_offset"]["pre"]
    post_test = TEST_DATA["pull_exif_no_offset"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--pull-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test


def test_select_zinnias(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(
        photoslib, suspend_capture, "multi-colored zinnia flowers"
    )


def test_pull_exif_no_data(photoslib, suspend_capture, output_file):
    """Test --pull-exif when photo has no data in EXIF"""
    pre_test = TEST_DATA["pull_exif_no_data"]["pre"]
    post_test = TEST_DATA["pull_exif_no_data"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--pull-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "Skipping update for missing EXIF data in photo" in result.output

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test

def test_pull_exif_no_data_use_file_time(photoslib, suspend_capture, output_file):
    """Test --pull-exif when photo has no data in EXIF with --use-file-time"""
    pre_test = TEST_DATA["pull_exif_no_data_use_file_time"]["pre"]
    post_test = TEST_DATA["pull_exif_no_data_use_file_time"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--pull-exif",
            "--plain",
            "--verbose",
            "--use-file-time",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "EXIF date/time missing, using file modify date/time" in result.output

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test



def test_select_sunset_video(photoslib, suspend_capture):
    """Force user to select the right photo for following tests"""
    assert ask_user_to_make_selection(photoslib, suspend_capture, "sunset", video=True)


@pytest.mark.parametrize("expected", TEST_DATA["compare_video_1"]["expected"])
def test_video_compare_exif(photoslib, suspend_capture, expected, output_file):
    """Test --compare-exif with video"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--compare-exif",
            "--plain",
            "-o",
            output_file,
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == expected


@pytest.mark.parametrize(
    "input_value,expected", TEST_DATA["video_date_delta"]["parameters"]
)
def test_video_date_delta(
    photoslib, suspend_capture, input_value, expected, output_file
):
    """Test --date-delta with video"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--date-delta",
            input_value,
            "--plain",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--inspect", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize(
    "input_value,expected", TEST_DATA["video_time_delta"]["parameters"]
)
def test_video_time_delta(
    photoslib, suspend_capture, input_value, expected, output_file
):
    """Test --time-delta with video"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--time-delta",
            input_value,
            "--plain",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli,
        ["--inspect", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["video_date"]["parameters"])
def test_video_date(photoslib, suspend_capture, input_value, expected, output_file):
    """Test --date with video"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--date",
            input_value,
            "--plain",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(
        cli,
        ["--inspect", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize("input_value,expected", TEST_DATA["video_time"]["parameters"])
def test_video_time(photoslib, suspend_capture, input_value, expected, output_file):
    """Test --time with video"""
    from photos_time_warp.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--time",
            input_value,
            "--plain",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(
        cli,
        ["--inspect", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


@pytest.mark.parametrize(
    "input_value,expected_date,expected_tz", TEST_DATA["video_time_zone"]["parameters"]
)
def test_video_time_zone(
    photoslib, suspend_capture, input_value, expected_date, expected_tz, output_file
):
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli, ["--inspect", "--plain", "-o", output_file], terminal_width=TERMINAL_WIDTH
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected_date
    assert output_values[0].tz_offset == expected_tz


@pytest.mark.parametrize("input_value,expected", TEST_DATA["video_match"]["parameters"])
def test_video_match(photoslib, suspend_capture, input_value, expected, output_file):
    """Test --timezone --match with video"""
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
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli,
        ["--inspect", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(output_file)
    assert output_values[0].date_tz == expected


def test_video_push_exif(photoslib, suspend_capture, output_file):
    """Test --push-exif with video"""
    pre_test = TEST_DATA["video_push_exif"]["pre"]
    post_test = TEST_DATA["video_push_exif"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--push-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test


def test_video_pull_exif(photoslib, suspend_capture, output_file):
    """Test --pull-exif with video"""
    pre_test = TEST_DATA["video_pull_exif"]["pre"]
    post_test = TEST_DATA["video_pull_exif"]["post"]

    from photos_time_warp.cli import cli

    runner = CliRunner()

    # update the photo so we know if the data is updated
    result = runner.invoke(
        cli,
        ["-z", "-0500", "-D", "+1 day", "-T", "-10 hours", "-m", "-V", "--plain"],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == pre_test

    result = runner.invoke(
        cli,
        [
            "--pull-exif",
            "--plain",
            "--verbose",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ["--compare-exif", "--plain", "-o", output_file],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(output_file)
    assert output_values[0] == post_test
