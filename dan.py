import os
import dataclasses
from dataclasses import dataclass
from glob import glob
from io import BytesIO
from pathlib import Path
from pprint import pprint
from time import sleep
from typing import List, Literal, Union
from urllib.parse import urlparse

import requests
from iptcinfo3 import IPTCInfo

MAX_FILENAME = 100
DOWNLOAD_DIR = Path("./download")


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
            return self.tag_string_artist.split(" ")

        return []

    @property
    def characters(self) -> List[str]:
        if self.tag_string_character:
            return self.tag_string_character.split(" ")

        return []

    @property
    def copyright(self) -> List[str]:
        if self.tag_string_copyright:
            return self.tag_string_copyright.split(" ")

        return []

    def get_name(self, artists: List[str], characters: List[str]) -> str:
        """Generate a possible filename to fix MAX_FILENAME"""
        artists_str = " ".join(artists)
        characters_str = " ".join(characters)

        if artists_str and characters_str:
            return f"{artists_str} - {characters_str} ID[{self.id}].{self.file_ext}"

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
                if (DOWNLOAD_DIR / series).is_dir():
                    break

        if series:
            base_dir = base_dir / series

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

    def download(self) -> None:
        if self.exists():
            print("skipping", self)
            # TODO if get_file_save_path() != existing then rename
            return

        res = requests.get(self.file_url)
        if self.file_ext == "jpgTODO":
            f = BytesIO(res.content)
            info = IPTCInfo(f, force=True, inp_charset="utf_8")
            keywords = []
            info["date-created"] = self.created_at
            if len(self.artists) == 1:
                # https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata#creator
                info["By-line"] = self.artists[0]
            else:
                keywords.extend(self.artists)
            # https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata#keywords
            print(info)
            # TODO strip keywords already in info['keywords']
            info["keywords"].append(keywords)
            # info.save_as("hmm.jpg")
        file_save_path = self.get_file_save_path()
        file_save_path.parent.mkdir(parents=True, exist_ok=True)
        # TODO if file exists: update tags or skip
        with open(file_save_path, "wb") as fh:
            fh.write(res.content)
            print("wrote", self, file_save_path)
        # set created/mtime
        # os.utime(file_save_path)


def get_posts(page_number=1) -> List[Post]:
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
    posts = get_posts()
    for post in posts:
        post.download()
        sleep(1)
