import pathlib
from roo.hashing import sha256path, validate_hash, md5path, validate_md5


def test_sha256path(fixture_file):
    assert (
        sha256path(fixture_file("DESCRIPTION")) ==
        "a562eba580d75d67aff91f703758ca731aba9b97b8fcfa2a762d4b53d11ec492"
    )


def test_validate_hash():
    assert validate_hash("sha256:1234")
    for broken in ["", ":", "hah :123", "sha:yo"]:
        assert not validate_hash(broken)


def test_md5path(fixture_file):
    assert (
        md5path(pathlib.Path(fixture_file("DESCRIPTION"))) ==
        "1f4816bcd242e7283055c62badc734d6"
    )


def test_validate_md5():
    assert validate_md5("d41d8cd98f00b204e9800998ecf8427e")
    for broken in ["d41d8cd98f00b204e9800998", ""]:
        assert not validate_md5(broken)
