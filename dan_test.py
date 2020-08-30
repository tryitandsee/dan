import factory

import dan


class PostFactory(factory.Factory):
    class Meta:
        model = dan.Post

    created_at = "2020-08-12T17:48:47.177-04:00"
    updated_at = "2020-08-11T23:55:27.535-04:00"
    # large_file_url = factory.Faker("image_url")
    file_url = factory.Faker("image_url")
    file_size = 285415
    file_ext = "png"
    md5 = "22a63cecfd85ac0bb46b22bf5571ee3c"
    rating = "s"
    source = factory.Faker("url")
    # tag_count = 1
    # tag_count_artist = 0
    # tag_count_character = 0
    # tag_count_copyright = 0
    # tag_count_general = 0
    # tag_count_meta = 1
    # combined tags from artist+character+copyright+general+meta
    tag_string = "tagme"
    tag_string_artist = ""
    tag_string_character = ""
    # series/properties associated
    tag_string_copyright = "dragonball"
    # freeform tags
    tag_string_general = ""
    tag_string_meta = "highres tagme"


def test_post_artist():
    post = PostFactory(tag_string_artist="leonardo michelangelo raphael donatello")

    artists = post.artists

    assert artists == ["leonardo", "michelangelo", "raphael", "donatello"]
