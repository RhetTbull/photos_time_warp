#!/usr/bin/env python

from setuptools import setup, find_packages
import sys
import os.path

if sys.version_info < (3, 7, 0):
    sys.stderr.write("ERROR: You need Python 3.7 or later to use photos_time_warp.\n")
    exit(1)

# we'll import stuff from the source tree, let's ensure is on the sys path
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

# read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

about = {}
with open(
    os.path.join(this_directory, "photos_time_warp", "_version.py"),
    mode="r",
    encoding="utf-8",
) as f:
    exec(f.read(), about)

setup(
    name="photos_time_warp",
    version=about["__version__"],
    description="Adjust date and/or time of photos in Apple Photos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Rhet Turnbull",
    author_email="rturnbull+git@gmail.com",
    url="https://github.com/RhetTbull/exif2findertags",
    project_urls={"GitHub": "https://github.com/RhetTbull/exif2findertags"},
    download_url="https://github.com/RhetTbull/exif2findertags",
    packages=find_packages(exclude=["tests", "utils"]),
    license="License :: OSI Approved :: MIT License",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "osxphotos>=0.42.82,<0.43.0",
        "click==8.0.1,<9.0.0",
        "cloup>=0.11.0,<0.12.0",
        "rich>=10.6.0,<11.0.0",
        "pytimeparse>=1.1.8,<1.2.0",
        "photoscript>=0.1.4,<0.2.0",
        "pyobjc-core",
        "tenacity>=8.0.1,<9.0.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "photos_time_warp=photos_time_warp.cli:cli",
            "ptw=photos_time_warp.cli:cli",
        ]
    },
    include_package_data=True,
)
