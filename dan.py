import os
import dataclasses
from dataclasses import dataclass
from glob import glob
from io import BytesIO
from pprint import pprint
from typing import List, Literal, Union
from urllib.parse import urlparse

import requests
from iptcinfo3 import IPTCInfo

DOWNLOAD_DIR = "./download"


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
    def filename(self) -> str:
        # TODO file length limit
        return f"ID[{self.id}].{self.file_ext}"

    def exists(self) -> Union[str, Literal[False]]:
        """Have we downloaded this file already?"""
        files = glob(f"{DOWNLOAD_DIR}/*ID[{self.id}].*")
        if not files:
            return False

        return files[0]

    def download(self) -> None:
        if self.exists():
            print("skipping", self)
            return

        # if file exists: update tags or skip
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
        with open(self.filename, "wb") as fh:
            fh.write(res.content)
            print("wrote", self, self.filename)
        # os.utime(self.filename)
        # set created/mtime
        # save


def get_posts() -> List[Post]:
    url = os.getenv("BOORU_URL")
    assert url
    url_bits = urlparse(url)
    res = requests.get(
        f"{url_bits.scheme}://{url_bits.hostname}/posts.json",
        auth=(url_bits.username, url_bits.password),
        params={"order": f"ordfav:{url_bits.username}"},
    )
    if not res.ok:
        pprint(res.json())

    return [Post(**x) for x in res.json() if "file_url" in x]


if __name__ == "__main__":
    posts = get_posts()
    print(posts)
