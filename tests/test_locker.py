import shutil
import pathlib

from roo.deptree.dependencies import RootDependency
from roo.deptree.transforms import lock_entries_to_deptree
from roo.deptree.traverse import traverse_depth_first
from roo.locker import Locker
from roo.parsers.lock import Lock, RootLockEntry
from roo.parsers.rproject import RProject
from roo.semver import parse_constraint
from roo.sources.source_group import create_source_group_from_config_list

from tests.conftest import chdir


def test_lock_file_sync(fixture_file, tmpdir):
    rproject_file = fixture_file("locker/rproject.toml")
    with chdir(tmpdir):
        shutil.copy(rproject_file, ".")
        rproject = RProject.parse(pathlib.Path("rproject.toml"))
        lock = Lock()
        locker = Locker()
        assert not locker.is_lock_file_sync(rproject, lock, False)
        lock = locker.lock(rproject, lock, False)
        assert lock.metadata.content_hash == rproject.content_hash
        assert locker.is_lock_file_sync(rproject, lock, False)
        assert (
            lock.entries[1].files[0].name ==
            "testthat_0.2.tar.gz"
        )
        assert (
            lock.entries[1].files[0].hash ==
            "sha256:f144d216235bcba3e1d59a9fda289eb7f73a3e98a08eb896d998b2b7e3f14ba4"  # noqa
        )


def test_lock_file_obeys_constraints(fixture_file, tmpdir):
    rproject_file = fixture_file("locker/rproject.toml")
    with chdir(tmpdir):
        shutil.copy(rproject_file, ".")
        rproject = RProject.parse(pathlib.Path("rproject.toml"))
        old_lock = Lock()
        locker = Locker()
        new_lock = locker.lock(rproject, old_lock, False)
        testthat = [p for p in new_lock.entries
                    if not isinstance(p, RootLockEntry) and
                    p.name == "testthat"][0]
        assert testthat.version == "0.2"


def test_lock_file_conservative(fixture_file, tmpdir):
    rproject_file = fixture_file("locker/rproject.toml")
    with chdir(tmpdir):
        shutil.copy(rproject_file, ".")
        rproject = RProject.parse(pathlib.Path("rproject.toml"))
        lock_file = Lock()
        locker = Locker()
        lock = locker.lock(rproject, lock_file, False)
        testthat = [p for p in lock.entries
                    if not isinstance(p, RootLockEntry) and
                    p.name == "testthat"][0]
        assert testthat.version == "0.2"

        rproject.dependencies[0].constraint = parse_constraint("0.1")
        lock = locker.lock(rproject, lock, True)

        testthat = [p for p in lock.entries if
                    not isinstance(p, RootLockEntry) and
                    p.name == "testthat"][0]
        assert testthat.version == "0.1"
        lock = locker.lock(rproject, lock, False)

        testthat = [p for p in lock.entries if
                    not isinstance(p, RootLockEntry) and
                    p.name == "testthat"][0]
        assert testthat.version == "0.1"


def test_dump_and_recreate_deptree(fixture_file, tmpdir):
    rproject_file = fixture_file("locker-2/rproject.toml")

    with chdir(tmpdir):
        shutil.copy(rproject_file, ".")
        rproject = RProject.parse(pathlib.Path("rproject.toml"))
        source_group = create_source_group_from_config_list(rproject.sources)
        lock_file = Lock()
        locker = Locker()
        lock = locker.lock(rproject, lock_file, False)

        root = lock_entries_to_deptree(source_group, lock.entries)

        found = [x.name for x in traverse_depth_first(root)
                 if not isinstance(x, RootDependency)]
        # Check at least the presence of the initial packages
        for entry in [
            'git2r', 'cli', 'shiny', 'devtools', 'testthat', 'pkgdown']:
            assert entry in found

        # Test that the size of the found ones is larger than the basic
        # packages above.

        assert len(found) > 6
