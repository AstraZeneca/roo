from roo.hashing import sha256path, validate_hash


def test_sha256path(fixture_file):
    assert (
        sha256path(fixture_file("DESCRIPTION")) ==
        "a562eba580d75d67aff91f703758ca731aba9b97b8fcfa2a762d4b53d11ec492"
    )


def test_validate_hash():
    assert validate_hash("sha256:1234")
    for broken in ["", ":", "hah :123", "sha:yo"]:
        assert not validate_hash(broken)
