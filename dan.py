#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import dataclasses
import re
import time
from dataclasses import dataclass
from glob import glob
from io import BytesIO
from pathlib import Path
from pprint import pprint
from typing import List, Literal, Tuple, Union
from urllib.parse import urlparse

import libxmp
import libxmp.utils
import requests
from libxmp.consts import XMP_NS_DC, XMP_NS_XMP

MAX_FILENAME = 100
DOWNLOAD_DIR = Path("./download")
# Tags that aren't useful to save locally
BANNED_TAGS = ("banned_artist",)

utc_offset = time.localtime().tm_gmtoff
parser = argparse.ArgumentParser(description="Download booru")
parser.add_argument(
    "--page", type=int, default=1, help="What page to start at (default: 1)"
)
parser.add_argument(
    "--fast-update",
    action="store_true",
    help="Stop pagination when we see a post again",
)

unsafe_chars_to_strip = re.compile(r"[!?:<]+")


def safe(s: str) -> str:
    """Adjust text make safe filenames"""
    s = s.replace("/", "_")
    return unsafe_chars_to_strip.sub("", s).rstrip(".")


def add_array_xmp(xmp, key: str, items: List[str]) -> None:
    """
    Mutate xmp to add items to an array (Bag Text) to DC (Dublin Core) metadata field
    """
    existing_items = []
    try:
        xmp.get_property(XMP_NS_DC, key)
        n = xmp.count_array_items(XMP_NS_DC, key)
        for idx in range(1, n + 1):
            existing_items.append(xmp.get_array_item(XMP_NS_DC, key, idx))
    except libxmp.XMPError:
        pass
    for item in items:
        if item not in existing_items:
            xmp.append_array_item(
                libxmp.consts.XMP_NS_DC,
                key,
                item,
                {"prop_array_is_ordered": True, "prop_value_is_array": True},
            )


@dataclass
class Post:
    id: int
    created_at: str
    updated_at: str
    file_url: str
    file_size: int
    file_ext: str
    md5: str
    rating: str
    source: str
    # combined tags from artist+character+copyright+general+meta
    tag_string: str
    tag_string_artist: str
    tag_string_character: str
    # series/properties associated
    tag_string_copyright: str
    # freeform tags
    tag_string_general: str
    tag_string_meta: str

    def __init__(self, **kwargs):
        """
        Ignore extra attrs we don't care about
        https://stackoverflow.com/questions/54678337/how-does-one-ignore-extra-arguments-passed-to-a-data-class/54678706#54678706
        """
        names = set([f.name for f in dataclasses.fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)

    def __repr__(self) -> str:
        tags = self.artists + self.characters
        if not tags:
            return str(self.id)

        if self.artists and self.characters:
            return " ".join(self.artists) + " - " + " ".join(self.characters)

        return " ".join(self.artists + self.characters)

    @property
    def artists(self) -> List[str]:
        if self.tag_string_artist:
            return [
                x for x in self.tag_string_artist.split(" ") if x not in BANNED_TAGS
            ]

        return []

    @property
    def characters(self) -> List[str]:
        if self.tag_string_character:
            return [
                x for x in self.tag_string_character.split(" ") if x not in BANNED_TAGS
            ]

        return []

    @property
    def copyright(self) -> List[str]:
        if self.tag_string_copyright:
            return [
                x for x in self.tag_string_copyright.split(" ") if x not in BANNED_TAGS
            ]

        return []

    def get_name(self, artists: List[str], characters: List[str]) -> str:
        """Generate a possible filename to fix MAX_FILENAME"""
        artists_str = safe(" ".join(artists))
        characters_str = safe(" ".join(characters))

        if artists_str and characters_str:
            return f"{characters_str} - {artists_str} ID[{self.id}].{self.file_ext}"

        if artists_str and not characters_str:
            return f"{artists_str} ID[{self.id}].{self.file_ext}"

        if not artists_str and characters_str:
            return f"{characters_str} ID[{self.id}].{self.file_ext}"

        return f"ID[{self.id}].{self.file_ext}"

    def get_file_save_path(self) -> Path:
        """
        Find a file name that fits within MAX_FILENAME and return it's path

        WISHLIST templated file paths like "%s/%aa - %cc"
        """
        base_dir = DOWNLOAD_DIR
        series = None
        if self.copyright:
            for series in reversed(self.copyright):
                if (DOWNLOAD_DIR / safe(series)).is_dir():
                    break

        if series:
            base_dir = base_dir / safe(series)

        artists_src = self.artists.copy()
        characters_src = self.characters.copy()
        artists_dst: List[str] = []
        characters_dst: List[str] = []
        while len(self.get_name(artists_dst, characters_dst)) < MAX_FILENAME and (
            artists_src or characters_src
        ):
            if artists_src:
                artists_dst.append(artists_src.pop(0))
                if len(self.get_name(artists_dst, characters_dst)) > MAX_FILENAME:
                    artists_dst.pop()
                    break

            if characters_src:
                characters_dst.append(characters_src.pop(0))
                if len(self.get_name(artists_dst, characters_dst)) > MAX_FILENAME:
                    characters_dst.pop()
                    break

        return base_dir / self.get_name(artists_dst, characters_dst)

    def exists(self) -> Union[Path, Literal[False]]:
        """Have we downloaded this file already?"""
        files = list(DOWNLOAD_DIR.glob(f"**/*ID[[]{self.id}[]].{self.file_ext}"))
        if not files:
            return False

        return files[0]

    def sync_iptc(self, file_path: Path) -> None:
        """
        Sync metadata to file.

        Take in a file path because there's no guarantee file is at
        self.get_file_save_path()

        Note to future self: it doesn't matter if you put a namespace in the
        name like "xmp:CreateDate" vs "CreateDate" or "dc:creator" vs "creator"
        """
        if self.file_ext not in ("jpg", "jpeg", "png"):
            return

        xmpfile = libxmp.XMPFiles(file_path=str(file_path), open_forupdate=True)
        xmp = xmpfile.get_xmp()
        if not xmp:
            # TODO why do some PNG files not return xmp?
            return

        # Existing meta, this isn't very useful on it's own
        # xmpdict = libxmp.utils.object_to_dict(xmp)

        # Set simple metadata fields
        # https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata#date-created
        try:
            xmp.get_property(XMP_NS_XMP, "CreateDate")
        except libxmp.XMPError:
            xmp.set_property(XMP_NS_XMP, "CreateDate", self.created_at)

        try:
            xmp.get_property(XMP_NS_XMP, "ModifyDate")
        except libxmp.XMPError:
            xmp.set_property(XMP_NS_XMP, "ModifyDate", self.updated_at)

        try:
            xmp.get_property(XMP_NS_XMP, "Rating")
        except libxmp.XMPError:
            # If we bookmarked it, we must like it, so set a default of "4"
            xmp.set_property(XMP_NS_XMP, "Rating", "4")

        # https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata#creator
        add_array_xmp(xmp, "creator", self.artists)

        # https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata#keywords
        add_array_xmp(
            xmp,
            "subject",
            self.copyright + self.characters + self.tag_string_general.split(" "),
        )

        if xmpfile.can_put_xmp(xmp):
            xmpfile.put_xmp(xmp)
        xmpfile.close_file()

    def download(self, update_only: bool = False) -> Tuple[Path, bool]:
        """
        Parameters
        ----------
        update_only
            To support fast updates, the moment we hit a duplicate, stop
            downloading, but keep updating existing files if they exist

        Returns
        -------
          file_path, created
        """
        existing_file = self.exists()
        file_save_path = self.get_file_save_path()
        file_save_path.parent.mkdir(parents=True, exist_ok=True)
        if existing_file:
            if file_save_path != existing_file:
                existing_file.rename(file_save_path)
            self.sync_iptc(file_save_path)
            created_at = dt.datetime.strptime(self.created_at, "%Y-%m-%dT%H:%M:%S.%f%z")
            created_at_sec = time.mktime(created_at.utctimetuple()) + utc_offset
            updated_at = dt.datetime.strptime(self.updated_at, "%Y-%m-%dT%H:%M:%S.%f%z")
            updated_at_sec = time.mktime(updated_at.utctimetuple()) + utc_offset
            os.utime(file_save_path, times=(created_at_sec, updated_at_sec))
            return file_save_path, False

        if update_only:
            return file_save_path, False

        res = requests.get(self.file_url)
        with open(file_save_path, "wb") as fh:
            fh.write(res.content)
        self.sync_iptc(file_save_path)
        created_at = dt.datetime.strptime(self.created_at, "%Y-%m-%dT%H:%M:%S.%f%z")
        created_at_sec = time.mktime(created_at.utctimetuple()) + utc_offset
        updated_at = dt.datetime.strptime(self.updated_at, "%Y-%m-%dT%H:%M:%S.%f%z")
        updated_at_sec = time.mktime(updated_at.utctimetuple()) + utc_offset
        os.utime(file_save_path, times=(created_at_sec, updated_at_sec))
        return file_save_path, True


def get_posts(page_number=1) -> List[Post]:
    """Get a page of posts"""
    url = os.getenv("BOORU_URL")
    assert url
    url_bits = urlparse(url)
    res = requests.get(
        f"{url_bits.scheme}://{url_bits.hostname}/posts.json",
        auth=(url_bits.username, url_bits.password),
        params={
            "tags": f"ordfav:{url_bits.username}",
            "page": page_number,
            "limit": 200,
        },
    )
    if not res.ok:
        pprint(res.json())

    return [Post(**x) for x in res.json() if "file_url" in x]


if __name__ == "__main__":
    args = parser.parse_args()
    page_number = args.page
    post_seen_again = False
    while True:
        posts = get_posts(page_number)
        for post in posts:
            local_path, created = post.download(update_only=post_seen_again)
            if created:
                time.sleep(2)
            else:
                post_seen_again = True
            print(page_number, "saved" if created else "skip ", local_path)
        page_number += 1
        if args.fast_update and post_seen_again:
            break
        if not posts:
            break
