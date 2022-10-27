import pytest

from roo.sources.remote_source import RemoteSource, PackageNotFoundError


def test_remote_source():
    source = RemoteSource("CRAN", "http://cloud.r-project.org/", proxy=None)
    assert source.priority == 0
    assert source.contrib_url == "http://cloud.r-project.org/src/contrib/"
    assert len(source.find_package_versions("testthat")) != 0
    package = source.find_package("testthat", "1.0.0")
    assert package.name == "testthat"
    assert package.version == "1.0.0"

    with pytest.raises(PackageNotFoundError):
        source.find_package("notexistent", "0.6.6")
