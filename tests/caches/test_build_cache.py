import os
import pathlib
from tests.conftest import chdir, FIXTURE_DIR

from roo.caches.build_cache import BuildCache


def test_build_cache(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("base")

    build_cache = BuildCache(
        "3.6.0", "x86_64-apple-darwin15.6.0", root_dir=pathlib.Path(tmpdir))
    assert not build_cache.has_build("dummy", "1.3.3")

    with chdir(FIXTURE_DIR):
        build_cache.add_build("dummy", "1.3.3", pathlib.Path("Rchecker"))

    assert build_cache.has_build("dummy", "1.3.3")
    assert (
        pathlib.Path(tmpdir) / "build" / "3.6.0" /
        "x86_64-apple-darwin15.6.0" / "dummy_1.3.3.tar.gz"
    ).exists()

    tmpdir2 = tmpdir_factory.mktemp("base")

    build_cache.restore_build("dummy", "1.3.3", tmpdir2)
    assert os.listdir(tmpdir2) == ["DESCRIPTION"]
