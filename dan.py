import os
from pprint import pprint
from urllib.parse import urlparse

import requests


class Post:
    def __init__(self, data):
        self.__dict__ = data


url = os.getenv("BOORU_URL")
url_bits = urlparse(url)
res = requests.get(
    f"{url_bits.scheme}://{url_bits.hostname}/posts.json",
    auth=(url_bits.username, url_bits.password),
    params={"order": f"ordfav:{url_bits.username}"},
)
if not res.ok:
    pprint(res.json())


pprint(res.json())
