import shutil
from pathlib import Path

import factory
import responses

import dan


def setup_module(module):
    dan.DOWNLOAD_DIR = Path("./test_download")
    shutil.rmtree(dan.DOWNLOAD_DIR, ignore_errors=True)


class PostFactory(factory.Factory):
    class Meta:
        model = dan.Post

    id = factory.Faker("pyint")
    created_at = "2020-08-12T17:48:47.177-04:00"
    updated_at = "2020-08-11T23:55:27.535-04:00"
    # large_file_url = factory.Faker("image_url")
    file_url = factory.Faker("image_url")
    file_size = 285415
    file_ext = "jpg"
    md5 = "22a63cecfd85ac0bb46b22bf5571ee3c"
    rating = "s"
    source = factory.Faker("url")
    # tag_count = 1
    # tag_count_artist = 0
    # tag_count_character = 0
    # tag_count_copyright = 0
    # tag_count_general = 0
    # tag_count_meta = 1
    tag_string = "tagme"
    tag_string_artist = ""
    tag_string_character = ""
    tag_string_copyright = "dragonball"
    tag_string_general = ""
    tag_string_meta = "highres tagme"


def test_post_artist():
    post = PostFactory(tag_string_artist="leonardo michelangelo raphael donatello")

    artists = post.artists

    assert artists == ["leonardo", "michelangelo", "raphael", "donatello"]


def test_get_name_no_artist_no_char():
    post = PostFactory(id=42)

    name = post.get_name([], [])

    assert name == "ID[42].jpg"


def test_get_name_with_artist_no_char():
    post = PostFactory(id=42)

    name = post.get_name(["leonardo", "michelangelo"], [])

    assert name == "[leonardo][michelangelo] ID[42].jpg"


def test_get_name_no_artist_with_char():
    post = PostFactory(id=42)

    name = post.get_name([], ["raphael", "donatello"])

    assert name == "[raphael][donatello] ID[42].jpg"


def test_get_name_with_artist_with_char():
    post = PostFactory(id=42)

    name = post.get_name(["leonardo", "michelangelo"], ["raphael", "donatello"])

    assert name == "[leonardo][michelangelo] - [raphael][donatello] ID[42].jpg"


def test_get_file_save_path():
    post = PostFactory(
        tag_string_artist=" ".join(factory.Faker("words", nb=80).generate()),
        tag_string_character=" ".join(factory.Faker("words", nb=80).generate()),
    )

    save_path = post.get_file_save_path()

    assert len(save_path.name) > 80
    assert len(save_path.name) <= dan.MAX_FILENAME


@responses.activate
def test_post_download():
    responses.add(
        responses.GET,
        "https://example.com/foo.jpg",
        open("./fixtures/horse.jpg", "rb").read(),
    )
    post = PostFactory(file_url="https://example.com/foo.jpg")

    post.download()


@responses.activate
def test_post_download_uses_existing_copyright_Dir():
    responses.add(
        responses.GET,
        "https://example.com/foo.jpg",
        open("./fixtures/horse.jpg", "rb").read(),
    )
    post = PostFactory(
        file_url="https://example.com/foo.jpg", tag_string_copyright="foo dragonball"
    )
    (dan.DOWNLOAD_DIR / "dragonball").mkdir(exist_ok=True)

    post.download()

    assert (dan.DOWNLOAD_DIR / "foo").exists() == False
