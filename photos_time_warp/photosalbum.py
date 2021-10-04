""" PhotosAlbum class to create an album in default Photos library and add photos to it """

from typing import List, Optional

from more_itertools import chunked
from photoscript import Photo, PhotosLibrary

from .utils import noop, pluralize


class PhotosAlbum:
    def __init__(self, name: str, verbose: Optional[callable] = None):
        self.name = name
        self.verbose = verbose or noop
        self.library = PhotosLibrary()

        album = self.library.album(name)
        if album is None:
            self.verbose(f"Creating Photos album '{self.name}'")
            album = self.library.create_album(name)
        self.album = album

    def add(self, photo: Photo):
        self.album.add([photo])
        self.verbose(
            f"Added {photo.filename} ({photo.uuid}) to album {self.name}"
        )

    def add_list(self, photo_list: List[Photo]):
        for photolist in chunked(photo_list, 10):
            self.album.add(photolist)
        photo_len = len(photo_list)
        self.verbose(
            f"Added {photo_len} {pluralize(photo_len, 'photo', 'photos')} to album {self.name}"
        )

    def photos(self):
        return self.album.photos()
