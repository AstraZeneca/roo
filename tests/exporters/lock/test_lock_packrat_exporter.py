import pathlib

from roo.exporters.lock.lock_packrat_exporter import LockPackratExporter
from roo.parsers.lock import Lock


def test_lock_export(fixture_file, tmpdir):
    lockfile = Lock.parse(fixture_file("simple", "roo.lock"))
    packrat_file = pathlib.Path(tmpdir, "packrat.lock")
    LockPackratExporter().export(lockfile, packrat_file)

    with open(packrat_file) as f:
        content = f.readlines()

    assert content == [
        'PackratFormat: 1.4\n',
        'PackratVersion: 0.5.0\n',
        'Repos: CRAN=https://cloud.r-project.org/, QS=https://cran.ma.imperial.ac.uk/\n',  # noqa: E501
        '\n',
        'Package: assertthat\n',
        'Source: CRAN\n',
        'Version: 0.2.1\n',
        '\n',
        'Package: rlang\n',
        'Source: CRAN\n',
        'Version: 0.4.2\n',
    ]
