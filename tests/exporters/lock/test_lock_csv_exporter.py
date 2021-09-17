import csv
import pathlib

from roo.exporters.lock.lock_csv_exporter import LockCSVExporter
from roo.parsers.lock import Lock


def test_lock_csv_export(fixture_file, tmpdir):
    lockfile = Lock.parse(fixture_file("simple", "roo.lock"))
    csv_file = pathlib.Path(tmpdir, "roo.csv")
    LockCSVExporter().export(lockfile, csv_file)

    content = []
    with open(csv_file) as f:
        for row in csv.reader(f):
            content.append(row)

    assert content == [
        ['assertthat', '0.2.1', 'https://cloud.r-project.org/',
         'assertthat_0.2.1.tar.gz',
         'sha256:85cf7fcc4753a8c86da9a6f454e46c2a58ffc70c4f47cac4d3e3bcefda2a9e9f',  # noqa: E501
         'dev'],
        ['rlang', '0.4.2', 'https://cloud.r-project.org/',
         'rlang_0.4.2.tar.gz',
         'sha256:fbd1c9cb81c94f769bd57079d7ef0682f27b971181340b2ed1e3ab79c2659f39',  # noqa: E501
         'main']]
