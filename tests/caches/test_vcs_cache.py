import pathlib

from roo.caches.vcs_store import VCSStore


def test_basic_vcs_store_usage(tmpdir):
    tmppath = pathlib.Path(str(tmpdir))
    cache = VCSStore(tmppath)

    url = "https://github.com/r-lib/testthat.git"
    assert cache.root_dir == tmppath
    assert cache.base_dir(url) == (
        tmppath / "vcs" / "github.com" /
        "52fae88b9a63105606cb5dac13d187204312eed115fc457f61709ca7b7f59773"
    )

    assert cache.clone_dir(url, "master") == (
        tmppath / "vcs" / "github.com" /
        "52fae88b9a63105606cb5dac13d187204312eed115fc457f61709ca7b7f59773" /
        "master"
    )

    cache.clone_dir(url, "master").mkdir(parents=True)
    (cache.clone_dir(url, "master") / "foobar").touch()
    assert (cache.clone_dir(url, "master") / "foobar").exists()

    cache.clear_clone(url, "master")

    assert not (cache.clone_dir(url, "master") / "foobar").exists()

    cache.clone_dir(url, "master").mkdir(parents=True)
    (cache.clone_dir(url, "master") / "foobar").touch()
    assert (cache.clone_dir(url, "master") / "foobar").exists()

    cache.clear()

    assert not (cache.clone_dir(url, "master") / "foobar").exists()
