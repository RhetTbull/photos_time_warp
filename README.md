# photos_time_warp 

Bulk adjust the date, time, or timezone for photos in Apple Photos. Works on macOS only.

photos_time_warp operates on photos selected in Apple Photos.  To use it, open Photos, select the photos for which you'd like to adjust the date/time/timezone, then run photos_time_warp from the command line:

`photos_time_warp --date 2021-09-10 --time-delta "-1 hour" --timezone -0700 --verbose`

This example sets the date for all selected photos to `2021-09-10`, subtracts 1 hour from the time of each photo, and sets the timezone of each photo to `GMT -07:00` (Pacific Daylight Time).

**Caution**: This app directly modifies your Photos library database using undocumented features.  It may corrupt, damage, or destroy your Photos library.  Use at your own caution.  I strongly recommend you make a backup of your Photos library before using this script (e.g. use Time Machine).  See also [Warranty](#Warranty). 

# Installation
I recommend you install `photos_time_warp` with [pipx](https://github.com/pipxproject/pipx). If you use `pipx`, you will not need to create a virtual environment as `pipx` takes care of this. The easiest way to do this on a Mac is to use [homebrew](https://brew.sh/):

- Open `Terminal` (search for `Terminal` in Spotlight or look in `Applications/Utilities`)
- Install `homebrew` according to instructions at [https://brew.sh/](https://brew.sh/)
- Type the following into Terminal: `brew install pipx`
- Then type this: `pipx install git+https://github.com/RhetTbull/photos_time_warp.git`
- Now you should be able to run `photos_time_warp` by typing: `photos_time_warp`

Once you've installed `photos_time_warp` with pipx, to upgrade to the latest version:

    pipx upgrade photos_time_warp


# Usage
```
$ photos_time_warp --help
Usage: python -m photos_time_warp [OPTIONS]

  Adjust date/time/timezone of photos in Apple Photos

Specify which photo properties to change: [at least 1 required]
  --date DATE          Set date for selected photos. Format is 'YYYY-MM-DD'.
  --date-delta DELTA   Adjust date for selected photos by DELTA. Format is one
                       of: '±D days', '±W weeks', '±D' where D is days
  --time TIME          Set time for selected photos. Format is one of
                       'HH:MM:SS', 'HH:MM:SS.fff', 'HH:MM'.
  --time-delta DELTA   Adjust time for selected photos by DELTA time. Format is
                       one of '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or
                       min), '±S seconds' (or sec), '±S' (where S is seconds)
  --timezone TIMEZONE  Set timezone for selected photos as offset from UTC.
                       Format is one of '±HH:MM', '±H:MM', or '±HHMM'

Settings:
  -V, --verbose        Show verbose output.
  -L, --library PHOTOS_LIBRARY_PATH
                       Path to Photos library (e.g. '~/Pictures/Photos\
                       Library.photoslibrary'. This is not likely needed as
                       photos_time_warp will usually be able to locate the path
                       to the open Photos library. Use --library only if you get
                       an error that the Photos library cannot be located.

Other options:
  --version            Show the version and exit.
  --help               Show this message and exit.
```

# Contributing

Feedback and contributions of all kinds welcome!  Please open an [issue](https://github.com/RhetTbull/exif2findertags/issues) if you would like to suggest enhancements or bug fixes.

# Related Projects

- [osxphotos](https://github.com/RhetTbull/osxphotos) export photos and metadata from Apple Photos.

# Warranty 

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
