import pathlib
import shutil
from unittest import mock

import pytest

from roo.environment import Environment, ExistentEnvironment, \
    _find_all_installed_r_homes, _get_plist_version, \
    _find_highest_active_version
from roo.files.rprofile import RProfile
from roo.installer import Installer
from roo.parsers.lock import Lock
from roo.r_executor import RBoundExecutor


class MockPackage:
    pass


def test_create_environment(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    assert env.base_dir == tmpdir
    assert env.env_dir == pathlib.Path(tmpdir) / ".envs" / "hello"
    assert not env.exists()

    env.init()
    assert env.exists()
    assert (pathlib.Path(tmpdir) / ".envs" / "hello").is_dir()

    with pytest.raises(ExistentEnvironment):
        env.init()

    with pytest.raises(ValueError):
        Environment(base_dir=pathlib.Path(tmpdir), name="")


def test_enable(tmpdir):
    env1 = Environment(base_dir=pathlib.Path(tmpdir), name="env1")
    env1.init()
    assert env1.is_enabled()

    env2 = Environment(base_dir=pathlib.Path(tmpdir), name="env2")
    assert not env2.is_enabled()
    env2.init()

    assert env2.is_enabled()
    assert not env1.is_enabled()


def test_overwrite_environment(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()

    env.init(overwrite=True)
    assert env.exists()


def test_create_additional_environment(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()

    assert RProfile(
        pathlib.Path(tmpdir, ".Rprofile")).enabled_environment == "hello"

    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello2")
    env.init()
    assert env.env_dir == pathlib.Path(tmpdir) / ".envs" / "hello2"
    assert env.env_dir.exists()
    assert env.exists()

    assert RProfile(
        pathlib.Path(tmpdir, ".Rprofile")).enabled_environment == "hello2"


def test_has_package(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()
    assert not env.has_package("maic")

    shutil.copy(fixture_file("simple", "roo.lock"), "roo.lock")
    lock_file = Lock.parse(pathlib.Path("roo.lock"))

    installer = Installer()
    installer.install_lockfile(lock_file, env)

    assert env.has_package("rlang")
    assert env.has_package("rlang", "0.4.2")


def test_executor(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    executor = env.executor()
    assert isinstance(executor, RBoundExecutor)
    assert executor.environment == env


def test_environment_remove(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")

    env.init()
    assert env.exists()

    env.remove()
    assert not env.exists()

    # Trying to remove an environment that doesn't exist
    with pytest.raises(IOError):
        env.remove()


def test_version_info(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")

    env.init()
    assert "version" in env.r_version_info
    assert "platform" in env.r_version_info


def test_find_all_installed_r(fixture_file):
    with mock.patch("platform.system") as mock_system, \
            mock.patch("roo.environment._BASE_WINDOWS_R_INSTALL_PATH",
                       pathlib.Path(fixture_file(
                           "r_installation_paths", "windows"))
                       ):
        mock_system.return_value = "Windows"

        installed = _find_all_installed_r_homes()
        for entry in [
                {
                    "home_path": fixture_file(
                        "r_installation_paths", "windows", "R-3.6.3"),
                    "executable_path": fixture_file(
                        "r_installation_paths", "windows", "R-3.6.3", "bin",
                        "R.exe"
                    ),
                    "version": "3.6.3",
                    "active": True
                },
                {
                    "home_path": fixture_file(
                        "r_installation_paths", "windows", "R-3.6.0"),
                    "executable_path": fixture_file(
                        "r_installation_paths", "windows", "R-3.6.0", "bin",
                        "R.exe"
                    ),
                    "version": "3.6.0",
                    "active": True
                }]:

            assert entry in installed

    with mock.patch("platform.system") as mock_system, \
            mock.patch("roo.environment._BASE_MACOS_R_INSTALL_PATH",
                       pathlib.Path(fixture_file(
                           "r_installation_paths", "macos"))
                       ):
        mock_system.return_value = "Darwin"

        installed = _find_all_installed_r_homes()

        for entry in [
                {
                    "home_path": fixture_file(
                        "r_installation_paths", "macos", "Versions", "3.6"),
                    "executable_path": fixture_file(
                        "r_installation_paths", "macos", "Versions", "3.6",
                        "Resources", "bin", "R"),
                    "version": "3.6.0",
                    "active": True
                },
                {
                    "home_path": fixture_file(
                        "r_installation_paths", "macos", "Versions", "4.1"),
                    "executable_path": fixture_file(
                        "r_installation_paths", "macos", "Versions", "4.1",
                        "Resources", "bin", "R"),
                    "version": "4.1.2",
                    "active": False
                }]:
            assert entry in installed


def test_get_plist_version(fixture_file):
    version = _get_plist_version(fixture_file("Info.plist"))
    assert version == "3.6.0"


def test_find_highest_version(fixture_file):
    with mock.patch("platform.system") as mock_system, \
            mock.patch("roo.environment._BASE_WINDOWS_R_INSTALL_PATH",
                       pathlib.Path(fixture_file(
                           "r_installation_paths", "windows"))
                       ):
        mock_system.return_value = "Windows"

        assert _find_highest_active_version() == {
            "home_path": fixture_file(
                "r_installation_paths", "windows", "R-3.6.3"
            ),
            "executable_path": fixture_file(
                "r_installation_paths", "windows", "R-3.6.3", "bin",
                "R.exe"
            ),
            "version": "3.6.3",
            "active": True
        }
