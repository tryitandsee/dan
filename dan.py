import os
import dataclasses
from dataclasses import dataclass
from pprint import pprint
from typing import List
from urllib.parse import urlparse

import requests


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

    def __str__(self) -> str:
        tags = self.artists + self.characters
        if not tags:
            return self.md5

        if self.artists and self.characters:
            return " ".join(self.artists) + " - " + " ".join(self.characters)

        return " ".join(self.artists + self.characters)

    def __repr__(self) -> str:
        return self.__str__()

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


def get_posts():
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
