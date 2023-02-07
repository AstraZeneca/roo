import pathlib
import shutil
from typing import cast
from unittest import mock

import pytest

from roo.caches.build_cache import BuildCache
from roo.environment import Environment
from roo.installer import Installer, InstallationError
from roo.sources.exceptions import PackageNotFoundError
from roo.parsers.lock import Lock, SourceLockEntry
from roo.locker import Locker
from roo.parsers.rproject import RProject
from tests.conftest import chdir


def test_installation_upgrade(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()

    version_info = env.r_version_info
    cache = BuildCache(version_info["version"], version_info["platform"])
    cache.clear()

    shutil.copy(fixture_file("simple", "roo.lock"), "roo.lock")
    lock_file = Lock.parse(pathlib.Path("roo.lock"))

    installer = Installer()
    installer.install_lockfile(lock_file, env)

    assert env.has_package("rlang", "0.4.2")
    entry = lock_file.entries[2]
    assert isinstance(entry, SourceLockEntry)
    entry = cast(SourceLockEntry, lock_file.entries[2])

    entry.version = "0.4.1"
    entry.files[0].name = "rlang_0.4.1.tar.gz"
    entry.files[0].hash = "sha256:13845846f27085279bfbb13986d56ff505486a38fe8c59e5e428e6760f835088"  # noqa

    installer.install_lockfile(lock_file, env)

    assert not env.has_package("rlang", "0.4.2")
    assert env.has_package("rlang", "0.4.1")


def test_installation_fails_for_missing_package(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()

    version_info = env.r_version_info
    cache = BuildCache(version_info["version"], version_info["platform"])
    cache.clear()

    shutil.copy(fixture_file("simple", "roo.lock"), "roo.lock")
    lock_file = Lock.parse(pathlib.Path("roo.lock"))
    entry = lock_file.entries[2]
    assert isinstance(entry, SourceLockEntry)
    entry.version = "0.0.0"
    entry.files[0].name = "rlang_0.0.0.tar.gz"
    entry.files[0].hash = "sha256:13845846f27085279bfbb13986d56ff505486a38fe8c59e5e428e6760f835088"  # noqa

    installer = Installer()

    with pytest.raises(PackageNotFoundError,
                       match="rlang 0.0.0"):
        installer.install_lockfile(lock_file, env)


def test_installation_fails_for_missing_r(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()

    version_info = env.r_version_info
    cache = BuildCache(version_info["version"], version_info["platform"])
    cache.clear()

    shutil.copy(fixture_file("simple", "roo.lock"), "roo.lock")
    lock_file = Lock.parse(pathlib.Path("roo.lock"))

    installer = Installer()
    with mock.patch("subprocess.check_call") as check_call_patched:
        check_call_patched.side_effect = FileNotFoundError()
        with pytest.raises(InstallationError,
                           match="Does the R executable exist?"):
            installer.install_lockfile(lock_file, env)


def test_install_with_wrong_sha(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()

    version_info = env.r_version_info
    cache = BuildCache(version_info["version"], version_info["platform"])
    cache.clear()

    with chdir(tmpdir):
        shutil.copy(fixture_file("simple", "roo.lock"), "roo.lock")
        lock_file = Lock.parse(pathlib.Path("roo.lock"))
        entry = cast(SourceLockEntry, lock_file.entries[1])
        entry.files[0].hash = "sha256:12345"
        installer = Installer()
        with pytest.raises(
                InstallationError,
                match=(
                    "Unable to install package assertthat 0.2.1"
                    " with incorrect hash"
                )):
            installer.install_lockfile(lock_file, env)


def test_install_from_vcs(fixture_file, tmpdir):
    rproject_file = fixture_file("git/rproject.toml")
    with chdir(tmpdir):
        shutil.copy(rproject_file, ".")
        rproject = RProject.parse(pathlib.Path("rproject.toml"))
        lock = Lock()
        locker = Locker()
        lock = locker.lock(rproject, lock, False)

        installer = Installer(verbose_build=True)
        env = Environment(pathlib.Path(str(tmpdir)), "test")
        env.init()

        installer.install_lockfile(lock, env)
        assert env.has_package("qscheck")
