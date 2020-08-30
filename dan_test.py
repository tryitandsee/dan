import factory

import dan


class PostFactory(factory.Factory):
    class Meta:
        model = dan.Post

    updated_at = "2020-08-11T23:55:27.535-04:00"
    large_file_url = "https://example.com/data/5e00fe186c8ce5b6ec406c743644367b.png"
    file_url = "https://example.com/data/5e00fe186c8ce5b6ec406c743644367b.png"
    file_size = 285415
    file_ext = "png"
    fav_count = 1
    tag_count = 1
    tag_count_artist = 0
    tag_count_character = 0
    tag_count_copyright = 0
    tag_count_general = 0
    tag_count_meta = 1
    tag_string = "tagme"
    tag_string_artist = ""
    tag_string_character = ""
    tag_string_copyright = ""
    tag_string_general = ""
    tag_string_meta = "tagme"


def test_hmm():
    assert False
