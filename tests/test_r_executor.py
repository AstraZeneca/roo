import pathlib
import subprocess
from unittest import mock

from roo.environment import Environment
from roo.r_executor import RBoundExecutor, RUnboundExecutor


def test_bound_executor(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    executor = RBoundExecutor(env)

    with mock.patch("subprocess.check_call") as check_call_patched:
        executor.install(fixture_file("Rchecker"))
        assert check_call_patched.call_args[0][0][1:] == [
            "CMD",
            "INSTALL",
            "-l",
            ".envs/hello/lib",
            str(fixture_file("Rchecker"))
        ]


def test_unbound_executor(fixture_file):
    executor = RUnboundExecutor(pathlib.Path("my/path/to/R.exe"))

    with mock.patch("subprocess.check_call") as check_call_patched:
        executor.install(fixture_file("Rchecker"))
        assert check_call_patched.call_args[0][0] == [
            "my/path/to/R.exe",
            "CMD",
            "INSTALL",
            str(fixture_file("Rchecker"))
        ]


def test_quiet_build(tmpdir, fixture_file):
    env = Environment(base_dir=pathlib.Path(tmpdir), name="hello")
    executor = RBoundExecutor(environment=env, quiet=True)

    with mock.patch("subprocess.check_call") as check_call_patched:
        executor.install(fixture_file("Rchecker"))
        assert check_call_patched.call_args[1]["stdout"] == subprocess.DEVNULL
        assert check_call_patched.call_args[1]["stderr"] == subprocess.DEVNULL

    executor = RBoundExecutor(environment=env, quiet=False)
    with mock.patch("subprocess.check_call") as check_call_patched:
        executor.install(fixture_file("Rchecker"))
        assert check_call_patched.call_args[1]["stdout"] != subprocess.DEVNULL
        assert check_call_patched.call_args[1]["stderr"] != subprocess.DEVNULL
