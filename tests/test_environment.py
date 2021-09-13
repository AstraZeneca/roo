import pathlib
import shutil
import textwrap

import pytest

from roo.environment import Environment
from roo.files.rprofile import rprofile_current_environment, \
    rprofile_set_environment, _find_rprofile_marker_zone
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

    with pytest.raises(IOError):
        env.init()


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

    assert rprofile_current_environment(
        pathlib.Path(tmpdir, ".Rprofile")) == "hello"

    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello2")
    env.init()
    assert env.env_dir == pathlib.Path(tmpdir) / ".envs" / "hello2"
    assert env.env_dir.exists()
    assert env.exists()

    assert rprofile_current_environment(
        pathlib.Path(tmpdir, ".Rprofile")) == "hello2"


def test_has_package(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    env.init()
    assert not env.has_package("maic")

    shutil.copy(fixture_file("simple", "rip.lock"), "rip.lock")
    lock_file = Lock.parse(pathlib.Path("rip.lock"))

    installer = Installer()
    installer.install_lockfile(lock_file, env)

    assert env.has_package("rlang")
    assert env.has_package("rlang", "0.4.2")


def test_executor(tmpdir):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    executor = env.executor()
    assert isinstance(executor, RBoundExecutor)
    assert executor.environment == env


def test_rprofile_set_environment_with_existent_file(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write("# A comment\n")

    rprofile_set_environment(rprofile_path, "foobar")

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # A comment
    # >>> created by rip
    enabled_env <- "foobar"
    source(file.path(".envs", enabled_env, "init.R"))
    # <<< created by rip
    """)


def test_rprofile_set_environment_from_nonexistent_file(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    rprofile_set_environment(rprofile_path, "foobar")

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # >>> created by rip
    enabled_env <- "foobar"
    source(file.path(".envs", enabled_env, "init.R"))
    # <<< created by rip
    """)


def test_rprofile_set_environment_with_already_present_env(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # >>> created by rip
            enabled_env <- "foobar"
            source(file.path(".envs", enabled_env, "init.R"))
            # <<< created by rip
            # This is a comment after the old entry
            """))

    rprofile_set_environment(rprofile_path, "barbaz")

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # This is comment before the old entry
    # This is a comment after the old entry
    # >>> created by rip
    enabled_env <- "barbaz"
    source(file.path(".envs", enabled_env, "init.R"))
    # <<< created by rip
    """)


def test_rprofile_set_environment_to_none(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # >>> created by rip
            enabled_env <- "foobar"
            source(file.path(".envs", enabled_env, "init.R"))
            # <<< created by rip
            # This is a comment after the old entry
            """))

    rprofile_set_environment(rprofile_path, None)

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # This is comment before the old entry
    # This is a comment after the old entry
    """)


def test_rprofile_current_environment(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # >>> created by rip
            enabled_env <- "foobar"
            source(file.path(".envs", enabled_env, "init.R"))
            # <<< created by rip
            # This is a comment after the old entry
            """))

    assert rprofile_current_environment(rprofile_path) == "foobar"

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # This is a comment after the old entry
            """))

    assert rprofile_current_environment(rprofile_path) is None


def test_find_rprofile_marker_zone():
    content = textwrap.dedent("""\
        # This is comment before the old entry
        # >>> created by rip
        enabled_env <- "foobar"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by rip
        # This is a comment after the old entry
        """).splitlines()

    assert _find_rprofile_marker_zone(content) == (1, 4)
    assert _find_rprofile_marker_zone([]) is None

    content = textwrap.dedent("""\
        # This is comment before the old entry
        # >>> created by rip
        enabled_env <- "foobar"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by rip
        # This is a comment after the old entry
        # >>> created by rip
        enabled_env <- "barbaz"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by rip
        # This is the second end
        """).splitlines()

    assert _find_rprofile_marker_zone(content) == (6, 9)

    content = textwrap.dedent("""\
        # This is comment before the old entry
        # >>> created by rip
        enabled_env <- "foobar"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by rip
        # This is a comment after the old entry
        # >>> created by rip
        enabled_env <- "barbaz"
        source(file.path(".envs", enabled_env, "init.R"))
        # This is the second end
        """).splitlines()

    assert _find_rprofile_marker_zone(content) is None

    content = textwrap.dedent("""\
        # Finds and end before a start
        # <<< created by rip
        # >>> created by rip
        enabled_env <- "barbaz"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by rip
        # This is the second end
        """).splitlines()

    assert _find_rprofile_marker_zone(content) == (2, 5)


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
