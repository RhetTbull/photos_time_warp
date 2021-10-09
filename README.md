# photos_time_warp 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

Batch adjust the date, time, or timezone for photos in Apple Photos. Works on macOS only.

photos_time_warp operates on photos selected in Apple Photos.  To use it, open Photos, select the photos for which you'd like to adjust the date/time/timezone, then run photos_time_warp from the command line:

`photos_time_warp --date 2021-09-10 --time-delta "-1 hour" --timezone -0700 --verbose`

This example sets the date for all selected photos to `2021-09-10`, subtracts 1 hour from the time of each photo, and sets the timezone of each photo to `GMT -07:00` (Pacific Daylight Time).

photos_time_warp has been well tested on macOS Catalina (10.15).  It should work on macOS Big Sur (11.0) and macOS Monterey (12.0) but I have not been able to test this.  It will not work on macOS Mojave (10.14) or earlier as the Photos database format is different.

**Caution**: This app directly modifies your Photos library database using undocumented features.  It may corrupt, damage, or destroy your Photos library.  Use at your own caution.  I strongly recommend you make a backup of your Photos library before using this script (e.g. use Time Machine).  See also [Warranty](#Warranty). 

## Examples 

### Add 1 day to the date of each photo**

`photos_time_warp --date-delta 1`

or

`photos_time_warp --date-delta "+1 day"`

### Set the date of each photo to 23 April 2020 and add 3 hours to the time

`photos_time_warp --date 2020-04-23 --time-delta "+3 hours"`

or

`photos_time_warp --date 2020-04-23 --time-delta "+03:00:00"`

### Set the time of each photo to 14:30 and set the timezone to UTC +1:00 (Central European Time)

`photos_time_warp --time 14:30 --timezone +01:00`

or

`photos_time_warp --time 14:30 --timezone +0100`

### Subtract 1 week from the date for each photo, add 3 hours to the time, set the timezone to UTC -07:00 (Pacific Daylight Time) and also use exiftool to update the EXIF metadata accordingly in the original file; use --verbose to print additional details

`photos_time_warp --date-delta "-1 week" --time-delta "+3 hours" --timezone -0700 --push-exif --verbose`

For this to work, you'll need to install the third-party [exiftool](https://exiftool.org/) utility.  If you use [homebrew](https://brew.sh/) you can do this with `brew install exiftool`.

### Set the timezone to UTC +03:00 for each photo but keep the time the same (that is, don't adjust time for the new timezone)

`photos_time_warp --timezone 0300 --match-time`

*Note on timezones and times*: In Photos, when you change the timezone, Photos assumes the time itself was correct for the previous timezone and adjusts the time accordingly to the new timezone.  E.g. if the photo's time is `13:00` and the timezone is `GMT -07:00` and you adjust the timezone one hour east to `GMT -06:00`, Photos will change the time of the photo to `14:00`.  photos_time_warp follows this behavior.  Using `--match-time` allows you to adjust the timezone but keep the same time without adjustment. For example, if your camera clock was correct but lacked timezone information and you took photos in one timezone but imported them to photos in another, Photos will add the timezone of the computer at time of import.  You can use photos_time_warp to adjust the timezone but keep the time using `--match-time`.

## Installation

I recommend you install `photos_time_warp` with [pipx](https://github.com/pipxproject/pipx).  The easiest way to do this on a Mac is to use [homebrew](https://brew.sh/):

- Open `Terminal` (search for `Terminal` in Spotlight or look in `Applications/Utilities`)
- Install `homebrew` according to instructions at [https://brew.sh/](https://brew.sh/)
- Type the following into Terminal: `brew install pipx`
- Then type this: `pipx install git+https://github.com/RhetTbull/photos_time_warp.git`
- Now you should be able to run `photos_time_warp` by typing: `photos_time_warp`.  
- *Note*: photos_time_warp will also install a shortcut command `ptw` that can be used to start photos_time_warp.

Once you've installed `photos_time_warp` with pipx, to upgrade to the latest version:

    pipx upgrade photos_time_warp


## Usage

```
$ photos_time_warp --help
Usage: photos_time_warp [OPTIONS]

  Adjust date/time/timezone of photos in Apple Photos. Changes will be applied
  to all photos currently selected in Photos. photos_time_warp cannot operate
  on photos selected in a Smart Album; select photos in a regular album or in
  the 'All Photos' view.

Specify one or more command: [at least 1 required]
  -d, --date DATE           Set date for selected photos. Format is 'YYYY-MM-
                            DD'.
  -D, --date-delta DELTA    Adjust date for selected photos by DELTA. Format is
                            one of: '±D days', '±W weeks', '±D' where D is days
  -t, --time TIME           Set time for selected photos. Format is one of
                            'HH:MM:SS', 'HH:MM:SS.fff', 'HH:MM'.
  -T, --time-delta DELTA    Adjust time for selected photos by DELTA time.
                            Format is one of '±HH:MM:SS', '±H hours' (or hr),
                            '±M minutes' (or min), '±S seconds' (or sec), '±S'
                            (where S is seconds)
  -z, --timezone TIMEZONE   Set timezone for selected photos as offset from
                            UTC. Format is one of '±HH:MM', '±H:MM', or
                            '±HHMM'. The actual time of the photo is not
                            adjusted which means, somewhat counterintuitively,
                            that the time in the new timezone will be
                            different. For example, if photo has time of 12:00
                            and timezone of GMT+01:00 and new timezone is
                            specified as '--timezone +02:00' (one hour ahead of
                            current GMT+01:00 timezone), the photo's new time
                            will be 13:00 GMT+02:00, which is equivalent to the
                            old time of 12:00+01:00. This is the same behavior
                            exhibited by Photos when manually adjusting
                            timezone in the Get Info window. See also --match-
                            time.
  -i, --inspect             Print out the date/time/timezone for each selected
                            photo without changing any information.
  -c, --compare-exif        Compare the EXIF date/time/timezone for each
                            selected photo to the same data in Photos. Requires
                            the third-party exiftool utility be installed (see
                            https://exiftool.org/). See also --add-to-album.
  -p, --push-exif           Push date/time and timezone for selected photos
                            from Photos to the EXIF metadata in the original
                            file in the Photos library. Requires the third-
                            party exiftool utility be installed (see
                            https://exiftool.org/). Using this option modifies
                            the *original* file of the image in your Photos
                            library. --push-exif will be executed after any
                            other updates are performed on the photo. See also
                            --pull-exif.
  -P, --pull-exif           Pull date/time and timezone for selected photos
                            from EXIF metadata in the original file into Photos
                            and update the associated data in Photos to match
                            the EXIF data. --pull-exif will be executed before
                            any other updates are performed on the photo. It is
                            possible for images to have missing EXIF data, for
                            example the date/time could be set but there might
                            be no timezone set in the EXIF metadata. Missing
                            data will be handled thusly: if date/time/timezone
                            are all present in the EXIF data, the photo's
                            date/time/timezone will be updated. If timezone is
                            missing but date/time is present, only the photo's
                            date/time will be updated.  If date/time is missing
                            but the timezone is present, only the photo's
                            timezone will be updated. If the date is present
                            but the time is missing, the time will be set to
                            00:00:00. Requires the third-party exiftool utility
                            be installed (see https://exiftool.org/). See also
                            --push-exif.

Options:
  -m, --match-time          When used with --timezone, adjusts the photo time
                            so that the timestamp in the new timezone matches
                            the timestamp in the old timezone. For example, if
                            photo has time of 12:00 and timezone of GMT+01:00
                            and new timezone is specified as '--timezone
                            +02:00' (one hour ahead of current GMT+01:00
                            timezone), the photo's new time will be 12:00
                            GMT+02:00. That is, the timezone will have changed
                            but the timestamp of the photo will match the
                            previous timestamp. Use --match-time when the
                            camera's time was correct for the time the photo
                            was taken but the timezone was missing or wrong and
                            you want to adjust the timezone while preserving
                            the photo's time. See also --timezone.
  -a, --add-to-album ALBUM  When used with --compare-exif, adds any photos with
                            date/time/timezone differences between Photos/EXIF
                            to album ALBUM.  If ALBUM does not exist, it will
                            be created.
  -V, --verbose             Show verbose output.
  -L, --library PHOTOS_LIBRARY_PATH
                            Path to Photos library (e.g. '~/Pictures/Photos\
                            Library.photoslibrary'). This is not likely needed
                            as photos_time_warp will usually be able to locate
                            the path to the open Photos library. Use --library
                            only if you get an error that the Photos library
                            cannot be located.
  -e, --exiftool-path PATH  Optional path to exiftool executable (will look in
                            $PATH if not specified) for those options which
                            require exiftool.

Other options:
  --version                 Show the version and exit.
  --help                    Show this message and exit.
```

## Implementation Details

This app is a bit of a hack.  Photos provides a way to change the date and time of a photo using AppleScript but does not provide a way to change the timezone.  Date/time adjustments are completed using AppleScript (via python using [PhotoScript](https://github.com/RhetTbull/PhotoScript)) and timezone adjustments are done by directly modifying the underlying Photos database (e.g. `~/Pictures/Photos\ Library.photoslibrary/database/Photos.sqlite`).  Apple does not document the structure of this database--a sqlite database which is actually a CoreData store--so it's possible this script modifies something it shouldn't (or fails to modify something it should) and thus corrupts the database.  I've spent considerable time reverse engineering the Photos database for the [osxphotos](https://github.com/RhetTbull/osxphotos/) project so I am fairly confident the modifications are safe...but, see the [Warranty](#Warranty).

If you want to peek even further under the hood, read on:

Photos maintains a lock on the database, even when Photos is closed, and the python [sqlite3](https://docs.python.org/3/library/sqlite3.html) API will not open the database while Photo's maintains its lock. This issue is unique to the python sqlite API; sqlite itself has no problem with this.  To get around this limitation, I use a [custom sqlite python wrapper](https://github.com/RhetTbull/photos_time_warp/blob/main/photos_time_warp/sqlite_native.py) that calls the system sqlite library directly using python's python-to-C API.  It's very hacky but appears to work OK (at least in my testing on macOS Catalina).

## Contributing

Feedback and contributions of all kinds welcome!  Please open an [issue](https://github.com/RhetTbull/photos_time_warp/issues) if you would like to suggest enhancements or bug fixes.

## Related Projects

- [osxphotos](https://github.com/RhetTbull/osxphotos) Export photos and metadata from Apple Photos.
- [exif2findertags](https://github.com/RhetTbull/exif2findertags) Read EXIF metadata from image and video files and convert it to macOS Finder tags and/or Finder comments.

## Warranty 

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="http://jmuccigr.github.io/"><img src="https://avatars.githubusercontent.com/u/615115?v=4?s=100" width="100px;" alt=""/><br /><sub><b>John Muccigrosso</b></sub></a><br /><a href="https://github.com/RhetTbull/photos_time_warp/issues?q=author%3AJmuccigr" title="Bug reports">🐛</a> <a href="#ideas-Jmuccigr" title="Ideas, Planning, & Feedback">🤔</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!