import pathlib

from roo.parsers.lock import Lock, Metadata, RootLockEntry, PackageFile, \
    SourceLockEntry, VCSLockEntry
from roo.parsers.rproject import Source


def test_lock_parsing(fixture_file):
    lockfile = Lock.parse(fixture_file("simple", "rip.lock"))

    assert len(lockfile.entries) == 3
    assert len(lockfile.sources) == 2
    assert lockfile.metadata.content_hash == "0403111a150fe98fb91ccf1f37fc86dd377ef6acd7083738d5596227dbf722a4"  # noqa
    assert str(lockfile.path).endswith("rip.lock")
    assert len(lockfile.entries[1].files) == 1


def test_empty_lock():
    lockfile = Lock()

    assert lockfile.path is None
    assert lockfile.entries == []
    assert lockfile.sources == []
    assert isinstance(lockfile.metadata, Metadata)
    assert lockfile.metadata.content_hash is None
    assert lockfile.metadata.env_id is None


def test_empty_lock_save(tmpdir):
    lockfile = Lock()
    assert not (tmpdir / "rip.lock").exists()
    lockfile.save(tmpdir / "rip.lock")
    assert (tmpdir / "rip.lock").exists()


def test_populated_lock_save(tmpdir):
    lockfile = Lock()
    lockfile.sources = [
        Source(name="QS", url="https://cran.ma.imperial.ac.uk/")
    ]

    lockfile.entries = [
        RootLockEntry(
            categories=["main"],
            dependencies=["mypackage", "otherpackage"]
        ),
        SourceLockEntry(
            name="mypackage",
            version="1.0.0",
            source="QS",
            categories=["main"],
            files=[
                PackageFile(name="mypackage-1.0.0.tar.gz", hash="sha:12345")
            ],
            dependencies=[]
        ),
        VCSLockEntry(
            name="otherpackage",
            vcs_type="git",
            url="https://github.com/AstraZeneca/qscheck.git",
            ref="master",
            categories=["main"],
            dependencies=[]
        )
    ]
    lockfile.metadata.content_hash = "123"
    lockfile.metadata.conservative = False
    lockfile.save(pathlib.Path(tmpdir / "rip.lock"))

    lockfile_read = Lock.parse(pathlib.Path(tmpdir / "rip.lock"))

    assert lockfile_read.metadata.content_hash == "123"
    assert not lockfile_read.metadata.conservative
    assert len(lockfile_read.entries) == 3
    entry = lockfile_read.entries[1]
    assert entry.version == "1.0.0"
    assert entry.source == "QS"
    assert entry.categories == ["main"]
    assert len(entry.files) == 1
    file = entry.files[0]
    assert file.name == "mypackage-1.0.0.tar.gz"
    assert file.hash == "sha:12345"

    entry = lockfile_read.entries[2]
    assert entry.name == "otherpackage"
    assert entry.vcs_type == "git"
    assert entry.url == "https://github.com/AstraZeneca/qscheck.git"
    assert entry.ref == "master"
    assert entry.categories == ["main"]


def test_lock_dependencies(tmpdir):
    lockfile = Lock()
    lockfile.sources = [
        Source(name="QS", url="https://cran.ma.imperial.ac.uk/")
    ]

    lockfile.entries = [
        SourceLockEntry(
            name="base",
            version="1.0.0",
            source="QS",
            categories=["main"],
            files=[
                    PackageFile(
                        name="base-1.0.0.tar.gz",
                        hash="sha:12345"
                    )
            ],
            dependencies=[]
        ),
        SourceLockEntry(
            name="derived",
            version="1.0.0",
            source="QS",
            categories=["main"],
            files=[
                PackageFile(
                    name="derived-1.0.0.tar.gz",
                    hash="sha:12345"
                )
            ],
            dependencies=["base"]
        ),
        SourceLockEntry(
            name="another",
            version="1.0.0",
            source="QS",
            categories=["main"],
            files=[
                    PackageFile(
                        name="another-1.0.0.tar.gz",
                        hash="sha:12345"
                    )],
            dependencies=["base", "derived"]
        ),
        VCSLockEntry(
            name="another",
            vcs_type="git",
            url="https://github.com/AstraZeneca/qscheck.git",
            ref="master",
            categories=["main"],
            dependencies=["base", "derived"]
        )
    ]

    lockfile.save(pathlib.Path(tmpdir / "rip.lock"))
    lockfile_read = Lock.parse(pathlib.Path(tmpdir / "rip.lock"))

    assert lockfile_read.entries[0].name == "another"
    assert "base" in lockfile_read.entries[0].dependencies
    assert "derived" in lockfile_read.entries[0].dependencies
