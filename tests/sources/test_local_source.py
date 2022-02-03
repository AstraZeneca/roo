import pathlib

import pytest
from roo.caches.source_cache import SourceCache

from roo.sources.local_source import LocalSource, PackageNotFoundError


def test_local_source(fixture_file, tmpdir):
    tmpdir_path = pathlib.Path(str(tmpdir))
    source = LocalSource("Local", str(fixture_file("LocalCRAN")))
    source._cache = SourceCache(
        str(fixture_file("LocalCRAN")),
        root_dir=tmpdir_path
    )

    assert "src/contrib" in str(source.contrib_path)
    assert "src/contrib/Archive" in str(source.archive_path)

    assert len(source.find_package_versions("Rchecker")) == 3
    assert sorted([pkg.version
                   for pkg in source.find_package_versions("Rchecker")]) == [
        "0.3.0", "0.5.0", "1.0.0",
    ]

    package = source.find_package("Rchecker", "1.0.0")
    assert package.name == "Rchecker"
    assert package.version == "1.0.0"
    assert package.versioned_name == "Rchecker_1.0.0"
    assert package.source == source
    assert package.filename == "Rchecker_1.0.0.tar.gz"
    assert package.local_path is None
    assert not package.has_local_file()

    package = source.find_package("Rchecker", "0.3.0")
    assert package.name == "Rchecker"
    assert package.version == "0.3.0"
    assert package.versioned_name == "Rchecker_0.3.0"
    assert package.source == source
    assert package.filename == "Rchecker_0.3.0.tar.gz"
    assert package.local_path is None
    assert not package.has_local_file()

    package.ensure_local()

    assert package.local_path is not None

    assert package.has_local_file()
    assert package.description is not None

    with pytest.raises(PackageNotFoundError):
        source.find_package("notexistent", "0.6.6")
