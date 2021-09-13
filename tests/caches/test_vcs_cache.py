import pathlib

from roo.caches.vcs_store import VCSStore


def test_basic_vcs_cache_usage(tmpdir):
    tmppath = pathlib.Path(str(tmpdir))
    cache = VCSStore("https://github.com/r-lib/testthat.git", tmppath)

    assert cache.root_dir == tmppath
    assert cache.base_dir == (
        tmppath / "vcs" / "github.com" /
        "52fae88b9a63105606cb5dac13d187204312eed115fc457f61709ca7b7f59773"
    )

    assert cache.clone_dir("master") == (
        tmppath / "vcs" / "github.com" /
        "52fae88b9a63105606cb5dac13d187204312eed115fc457f61709ca7b7f59773" /
        "master"
    )

    cache.clone_dir("master").mkdir(parents=True)
    (cache.clone_dir("master") / "foobar").touch()
    assert (cache.clone_dir("master") / "foobar").exists()

    cache.clear_clone("master")

    assert not (cache.clone_dir("master") / "foobar").exists()

    cache.clone_dir("master").mkdir(parents=True)
    (cache.clone_dir("master") / "foobar").touch()
    assert (cache.clone_dir("master") / "foobar").exists()

    cache.clear()

    assert not (cache.clone_dir("master") / "foobar").exists()
