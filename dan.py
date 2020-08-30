import os
from pprint import pprint
from urllib.parse import urlparse

import requests


class Post:
    def __init__(self, data=None, **init_kwargs):
        if data is None:
            # TODO get Factory Boy to initialize w/ data
            self.__dict__ = init_kwargs
        else:
            self.__dict__ = data

    def __str__(self):
        tags = self.artists + self.characters
        if not tags:
            return self.md5

        if self.artists and self.characters:
            return " ".join(self.artists) + " - " + " ".join(self.characters)

        return " ".join(self.artists + self.characters)

    def __repr__(self):
        return self.__str__()

    @property
    def artists(self):
        if self.tag_string_artist:
            return self.tag_string_artist.split(" ")

        return []

    @property
    def characters(self):
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

    return [Post(x) for x in res.json() if "file_url" in x]


if __name__ == "__main__":
    posts = get_posts()
    print(posts)
