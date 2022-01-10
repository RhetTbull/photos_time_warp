# Tests for photos_time_warp

These tests are interactive.  The test script will copy a test album to your Pictures folder then open this library in Photos. You'll then be prompted to select certain photos in Photos followed by pressing "Enter" in the terminal.

The tests must be run in order as each tests modifies the metadata associated with the photo or video being tested and subsequent tests assume the modified metadata as a starting point.

The tests require the use a small Photos library with some photos in it. The photos are all copyright Rhet Turnbull, 2021.  The photos may be freely used under the terms of the [Creative Commons Attribution 4.0 International (CC BY 4.0) license](https://creativecommons.org/licenses/by/4.0/).

**WARNING**: Do not open the test photo libraries in the tests/ folder.  Doing so will cause Photos to track these libraries (and make updates to the database as Photos performs machine learning, etc.) which will cause unnecessary changes to the files under version control.  If you need to manipulate or view the test libraries, copy them to your ~/Pictures folder and open them there then copy the libraries back to the tests/ folder.