from roo.caches.source_cache import SourceCache


def test_source_cache():
    cache = SourceCache("http://cran.r-project.org")

    assert str(cache.root_dir).endswith(".rip/cache")
    assert str(cache.base_dir).endswith(
        ".rip/cache/source/cran.r-project.org/"
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
