import typing
from typing import Union
import logging
import pathlib
import shutil
import platform
import toml
from .files.rprofile import rprofile_current_environment, \
    rprofile_set_environment

from .parsers.description import Description
from .parsers.exceptions import ParsingError

from .r_executor import RBoundExecutor, RUnboundExecutor

logger = logging.getLogger(__file__)


class UnexistentEnvironment(Exception):
    pass


class Environment:
    """Describes an environment at a given directory.
    """

    def __init__(self, base_dir: pathlib.Path, name: str):
        """
        Instantiates the environment that may or may not exist.

        Args:
            base_dir: the base directory where the .rprofile and .envs
                      will be created.
                      This will be cast to an absolute path if relative.
            name: The name of the environment
        """
        # Contains always the absolute path of the environment base.
        self.base_dir = base_dir.absolute()

        # The name of the environment
        self.name = name

    @property
    def r_version_info(self) -> dict:
        return self.executor().version_info

    @property
    def env_dir(self) -> pathlib.Path:
        """Returns the absolute path to the environment directory"""
        return self.base_dir / self.env_reldir

    @property
    def lib_dir(self) -> pathlib.Path:
        """Returns the absolute path to the lib dir"""
        return self.base_dir / self.lib_reldir

    @property
    def env_reldir(self) -> pathlib.Path:
        """Returns a relative path to the environment directory"""
        return pathlib.Path(".envs") / self.name

    @property
    def lib_reldir(self) -> pathlib.Path:
        """Returns a relative path to the lib dir"""
        return self.env_reldir / "lib"

    def exists(self):
        """Returns true if the environment exists at that location"""
        return (self.env_dir / "init.R").exists()

    def enable(self, enabled: bool) -> None:
        """
        Enables or disables this environment depending on the enabled flag.

        Args:
            enabled: True to enable the environment. False to disable.
        """
        if not self.exists():
            raise UnexistentEnvironment()

        rprofile_path = pathlib.Path(self.base_dir) / ".Rprofile"
        name = self.name if enabled else None
        rprofile_set_environment(rprofile_path, name)

    def is_enabled(self) -> bool:
        """
        Returns True if this environment is enabled, otherwise False.
        """
        rprofile_path = pathlib.Path(self.base_dir) / ".Rprofile"
        return rprofile_current_environment(rprofile_path) == self.name

    def remove(self) -> None:
        """
        Removes an environment completely.
        """
        if not self.exists():
            raise IOError("The environment does not exist")

        self.enable(False)

        shutil.rmtree(self.env_dir)

    def init(self,
             r_executable_path: Union[pathlib.Path, None] = None,
             overwrite: bool = False) -> None:
        """Initializes the environment

        Args:
            r_executable_path: if specified, which R to use to create the env.
                               if not specified, one will be found.
            overwrite: If true, overwrite a pre-existing environment,
                       otherwise raise an error.
        """

        if self.exists():
            if not overwrite:
                raise IOError(f"Environment {self.name} already existent in "
                              + f"{self.base_dir}")
            self.remove()

        if r_executable_path is None:
            r_executable_path = _find_r_executable_path()
        else:
            if not r_executable_path.is_file():
                raise FileNotFoundError(
                    f"Specified R executable {r_executable_path} does not "
                    f"exist or is not a file"
                )

        # create the new environment
        self.env_dir.mkdir(parents=True, exist_ok=False)
        self.lib_dir.mkdir(parents=True, exist_ok=False)
        self._create_initr()
        self._create_renv_config(r_executable_path)
        self.enable(True)

    def has_package(self, name: str, version: Union[str, None] = None) -> bool:
        """
        Returns true if the environment has a given package.
        Args:
            name: The name of the package
            version: optional, the specific version of the package.
                     If unspecified, only the name is considered.

        Returns: True if the package is present. False otherwise

        """
        current_version = self.package_version(name)
        if current_version is None:
            return False

        if version is None:
            return True

        return current_version == version

    def package_version(self, name: str) -> Union[str, None]:
        """
        Returns the current version of the package with a given name,
        or None if the package is not present
        Args:
            name: the name of the package

        Returns: the package version or None if not present

        """
        package_dir = self.lib_dir / name
        if not package_dir.exists():
            return None

        description_path = package_dir / "DESCRIPTION"

        try:
            desc = Description.parse(description_path)
        except ParsingError:
            return None

        return desc.version

    def executor(self) -> RBoundExecutor:
        """Returns a R executor attached to the specified environment"""
        return RBoundExecutor(self)

    @property
    def r_executable_path(self) -> pathlib.Path:
        """Returns the R executable path to invoke for this environment.
        For backward compatibility, if there is no configuration file
        it will look for a reasonable path and use that.
        """
        try:
            with open(self.env_dir / "renv.toml", "r", encoding="utf-8") as f:
                data = toml.load(f)
        except FileNotFoundError:
            data = {}

        try:
            return pathlib.Path(data["r_executable_path"])
        except KeyError:
            return _find_r_executable_path()

    def _create_initr(self):
        """Create an init.R file in case it doesn't exist"""
        with open(self.env_dir / "init.R", "w", encoding="utf-8") as f:
            f.write(f"message('Using environment {self.name}')\n")
            f.write(f".libPaths(c('{self.lib_reldir.as_posix()}'))\n")

    def _create_renv_config(self, r_executable_path):
        executor = RUnboundExecutor(r_executable_path=r_executable_path)
        version_info = executor.version_info

        # Also store the version info in the configuration file.
        # we will parse it from the init later on so that if we accidentally
        # invoke the environment with the wrong version of R we can
        # stop and warn the user.
        with open(self.env_dir / "renv.toml", "w", encoding="utf-8") as f:
            toml.dump({
                "r_executable_path": str(r_executable_path),
                "r_version": version_info["version"],
                "r_platform": version_info["platform"],
            }, f)


def available_environments(base_dir: pathlib.Path) -> typing.List[Environment]:
    """
    Returns a list of all available environments in base_dir
    """
    environments = []
    for entry in (base_dir / ".envs").iterdir():
        if not entry.is_dir():
            continue

        try:
            env = Environment(base_dir, entry.name)
            if env.exists():
                environments.append(env)
        except IOError:
            pass

    return environments


def enabled_environment(base_dir: pathlib.Path) -> Union[Environment, None]:
    """Returns the currently active environment, or None if no
    active environment"""

    for env in available_environments(base_dir):
        if env.is_enabled():
            return env

    return None


def _find_r_executable_path() -> pathlib.Path:
    """
    Finds the R installation available on the machine,
    trying all possible options and just reverting to a simple "R"
    invocation if all else fails.
    """

    plat = platform.system()
    candidates = []
    if plat == "Windows":
        candidates = [
            "C:\\Program Files\\R\\R-3.6.3\\bin\\R.exe",
            "C:\\Program Files\\R\\R-3.6.0\\bin\\R.exe",
        ]
        which = shutil.which("R.exe")
        if which is not None:
            candidates.append(which)
    elif plat == "Linux":
        candidates = ["/usr/local/bin/R"]
        which = shutil.which("R")
        if which is not None:
            candidates.append(which)
    elif plat == "Darwin":
        candidates = ["/usr/local/bin/R"]
        which = shutil.which("R")
        if which is not None:
            candidates.append(which)
    else:
        raise RuntimeError(f"Unknown platform {plat}")

    for candidate in candidates:
        candidate_path = pathlib.Path(candidate)
        if candidate_path.is_file():
            return candidate_path

    raise FileNotFoundError(
        f"Unable to find an R installation at {candidates}"
    )
