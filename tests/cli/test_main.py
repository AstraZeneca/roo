import pathlib
import shutil

from click.testing import CliRunner
from roo.cli.__main__ import (
    init, environment_init, cache_clear, lock, export_lock,
    package_dependencies, install)

from tests.conftest import chdir


def test_init(tmpdir):
    runner = CliRunner()
    with chdir(tmpdir):
        result = runner.invoke(init)
        assert result.exit_code == 0
        assert pathlib.Path("rproject.toml").exists()


def test_environment_init(tmpdir):
    runner = CliRunner()
    with chdir(tmpdir):
        result = runner.invoke(environment_init, ["env1"])
        assert result.exit_code == 0
        assert pathlib.Path(".envs/env1").exists()
        assert pathlib.Path(".Rprofile").exists()

        result = runner.invoke(environment_init, ["env1"])
        assert "Environment env1 already existent" in result.output
        assert result.exit_code == 1

        # Create a dummy file to see if the environment is actually deleted
        sentinel_path = pathlib.Path(".envs/env1/hello")
        sentinel_path.touch()
        assert sentinel_path.exists()

        result = runner.invoke(environment_init, ["--overwrite", "env1"])
        assert result.exit_code == 0

        assert not sentinel_path.exists()


def test_cache_clear():
    cache_dir = pathlib.Path("~/.rip/cache").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    with open(cache_dir / "testfile", "w") as f:
        f.write("hello")

    runner = CliRunner()
    res = runner.invoke(cache_clear)
    assert res.exit_code == 0

    assert not pathlib.Path("~/.rip/cache/testfile").expanduser().exists()


def test_lock_overwrite(tmpdir):
    runner = CliRunner()

    with chdir(tmpdir):
        lock_path = pathlib.Path(".") / "rip.lock"
        with open(lock_path, "w") as f:
            f.write("Test")
        assert lock_path.exists()

        toml_path = pathlib.Path(".") / "rproject.toml"
        with open(toml_path, "w") as f:
            f.write("[tool.rip]\n")
            f.write("repositories = []\n")
            f.write("[tool.rip.dependencies]")
        assert toml_path.exists()

        result = runner.invoke(lock, ["--overwrite"])
        assert result.exit_code == 0


def test_export_lock(fixture_file, tmpdir):
    runner = CliRunner()

    with chdir(tmpdir):
        shutil.copyfile(fixture_file("simple", "rproject.toml"),
                        pathlib.Path(tmpdir) / "rproject.toml")
        res = runner.invoke(export_lock, ["csv", "rip.csv"])
        assert res.exit_code == 0


def test_package_dependencies(fixture_file, tmpdir):
    runner = CliRunner()

    with chdir(tmpdir):
        shutil.copyfile(fixture_file("simple", "rproject.toml"),
                        pathlib.Path(tmpdir) / "rproject.toml")
        res = runner.invoke(package_dependencies, ["assertthat", "0.2.1"])

        assert res.exit_code == 0


def test_install(fixture_file, tmpdir):
    runner = CliRunner()

    with chdir(tmpdir):
        shutil.copyfile(fixture_file("simple", "rproject.toml"),
                        pathlib.Path(tmpdir) / "rproject.toml")

        result = runner.invoke(install, ["--env-overwrite"])
        assert result.exit_code == 0
