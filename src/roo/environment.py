import re
from xml.etree import ElementTree
import textwrap
from typing import Union, List, Dict, cast, Optional
import logging
import pathlib
import shutil
import subprocess
import platform
import toml
from .files.rprofile import RProfile

from .parsers.description import Description
from .parsers.exceptions import ParsingError

from .r_executor import RBoundExecutor, RUnboundExecutor

logger = logging.getLogger(__file__)


class UnexistentEnvironment(Exception):
    pass


class ExistentEnvironment(Exception):
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
        if name != name.strip():
            raise ValueError(
                "The environment name must not start or end with whitespace")

        if "/" in name or "\\" in name:
            raise ValueError(
                "The environment name must not contain / or \\")

        # The name of the environment
        name = name.strip()
        if len(name) == 0:
            raise ValueError("The environment name cannot be empty")

        self.name = name

    @property
    def r_version_info(self) -> dict:
        with open(self.env_dir / "renv.toml", "r", encoding="utf-8") as f:
            data = toml.load(f)

        return {
            "version": data["r_version"],
            "platform": data["r_platform"]
        }

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
        RProfile(rprofile_path).enabled_environment = name

    def is_enabled(self) -> bool:
        """
        Returns True if this environment is enabled, otherwise False.
        """
        rprofile_path = pathlib.Path(self.base_dir) / ".Rprofile"
        return RProfile(rprofile_path).enabled_environment == self.name

    def remove(self) -> None:
        """
        Removes an environment completely.
        """
        if not self.exists():
            raise IOError("The environment does not exist")

        self.enable(False)

        shutil.rmtree(self.env_dir)

    def init(self,
             r_version: Optional[str] = None,
             r_executable_path: Optional[pathlib.Path] = None,
             overwrite: bool = False) -> None:
        """Initializes the environment

        Args:
            r_executable_path: if specified, which R to use to create the env.
                               if not specified, one will be found.
            overwrite: If true, overwrite a pre-existing environment,
                       otherwise raise an error.
        """

        if r_version is not None and r_executable_path is not None:
            raise ValueError(
                "Cannot specify both R version and R executable path"
            )

        if self.exists():
            if not overwrite:
                raise ExistentEnvironment(
                    f"Environment {self.name} already existent in "
                    + f"{self.base_dir}")
            self.remove()

        if r_executable_path is None:
            r_executable_path = _find_r_executable_path(r_version)

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

    def executor(self, **options) -> RBoundExecutor:
        """Returns a R executor attached to the specified environment"""
        return RBoundExecutor(self, **options)

    @property
    def r_executable_path(self) -> pathlib.Path:
        """Returns the R executable path to invoke for this environment.
        """
        try:
            with open(self.env_dir / "renv.toml", "r", encoding="utf-8") as f:
                data = toml.load(f)
        except FileNotFoundError:
            data = {}

        try:
            return pathlib.Path(data["r_executable_path"])
        except KeyError:
            raise KeyError("Unable to find executable path in renv.toml")

    def _create_initr(self):
        """Create an init.R file in case it doesn't exist"""
        renv_path = self.env_reldir / "renv.toml"
        code = textwrap.dedent(f"""
            .parse_config_file <- function() {{
                out <- list()
                renv <- readLines('{renv_path.as_posix()}')
                for (line_num in seq_along(renv)) {{
                    line <- renv[[line_num]]
                    m <- regmatches(
                        line,
                        regexec("(.+?)\\\\s*=\\\\s*(\\")(.+)(\\")",
                        line, perl=TRUE)
                    )

                    key <- m[[1]][[2]]
                    val <- m[[1]][[4]]
                    out[[key]] <- val
                }}

                return(out)
            }}
            """
                               )

        code += textwrap.dedent(f"""
            config <- .parse_config_file()

            message(
                paste0(
                    'Using environment {self.name} ',
                    '(R version: ', config$r_version, ', ',
                    'platform: ', config$r_platform, ')'
                )
            )
            if (config$r_platform != R.version$platform) {{
                stop(
                    paste(
                        "Cannot use environment with current R platform",
                        R.version$platform
                    )
                )
            }}
            current_r_version <- paste0(R.version$major, ".", R.version$minor)
            if (config$r_version != current_r_version) {{
                stop(
                    paste(
                        "Cannot use environment with current R version",
                        current_r_version
                    )
                )
            }}

            .libPaths(c('{self.lib_reldir.as_posix()}'))

            """)

        with open(self.env_dir / "init.R", "w", encoding="utf-8") as f:
            f.write(code)

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


def available_environments(base_dir: pathlib.Path) -> List[Environment]:
    """
    Returns a list of all available environments in base_dir
    """
    environments: List[Environment] = []
    if not (base_dir / ".envs").exists():
        return environments

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


def _find_r_executable_path(r_version: Optional[str] = None) -> pathlib.Path:
    """
    Finds the R installation available on the machine.
    """

    # The approach is that we try first to find the all installed homes
    # and pick the highest active version. If nothing else works, we just
    # use whatever which R returns.

    if r_version is not None:
        active = _find_active_r_version(r_version)
        if active is None:
            raise FileNotFoundError(
                f"Unable to find active R executable for version {r_version}"
            )
        return cast(pathlib.Path, active["executable_path"])

    active = _find_highest_active_version()
    if active is not None:
        return cast(pathlib.Path, active["executable_path"])

    # Fallback on the result of the which command.
    plat = platform.system()
    if plat == "Windows":
        which = shutil.which("R.exe")
    else:
        which = shutil.which("R")

    if which is None:
        raise FileNotFoundError(
            "Unable to find R executable path anywhere")

    return pathlib.Path(which)


_BASE_WINDOWS_R_INSTALL_PATH = pathlib.Path(r"C:\Program Files\R")
_BASE_MACOS_R_INSTALL_PATH = pathlib.Path("/Library/Frameworks/R.framework/")
_BASE_LINUX_R_INSTALL_PATH_LIST = [
    pathlib.Path("/usr/lib/R/"),
    pathlib.Path("/usr/local/")
]


def find_all_installed_r_homes() -> List[Dict]:
    """Finds all available installed R homes.
    The order is arbitrary and depends on filesystem ordering.
    Priority must be decided outside.
    """
    plat = platform.system()
    installed_r = []
    if plat == "Windows":
        try:
            for entry in _BASE_WINDOWS_R_INSTALL_PATH.iterdir():
                m = re.match(r"R-(\d+\.\d+\.\d+)", str(entry.name))
                if m is not None:
                    installed_r.append({
                        "home_path": entry,
                        "executable_path": entry / "bin" / "R.exe",
                        "version": m.group(1),
                        "active": True
                    })
        except FileNotFoundError:
            pass
    elif plat == "Darwin":
        try:
            for entry in (_BASE_MACOS_R_INSTALL_PATH / "Versions").iterdir():
                if re.match(r"\d+\.\d+", str(entry.name)):
                    version = _get_plist_version(
                        entry / "Resources" / "Info.plist"
                    )
                    installed_r.append({
                        "home_path": entry,
                        "executable_path": entry / "Resources" / "bin" / "R",
                        "version": version,
                        "active": False,
                    })

            runnable_version = _get_plist_version(
                _BASE_MACOS_R_INSTALL_PATH / "Versions" /
                "Current" / "Resources" / "Info.plist"
            )

            for r_entry in installed_r:
                if r_entry["version"] == runnable_version:
                    r_entry["active"] = True
        except (FileNotFoundError, KeyError):
            pass
    elif plat == "Linux":
        # First, try with the base paths
        for base_path in _BASE_LINUX_R_INSTALL_PATH_LIST:
            try:
                version = _get_r_version(base_path / "bin" / "R")
                installed_r.append({
                    "home_path": base_path,
                    "executable_path": base_path / "bin" / "R",
                    "version": version,
                    "active": True,
                })
            except (FileNotFoundError,
                    subprocess.CalledProcessError,
                    KeyError):
                logger.exception("Failed option")

        # also try under opt, one version per subdir, which is how github
        # seem to do it. We really need to make this whole detection
        # thing configurable
        try:
            base_path = pathlib.Path("/opt/R/")
            for entry in base_path.iterdir():
                logger.info(f"Trying {entry.name}")
                if re.match(r"\d+\.\d+\.\d+", str(entry.name)):
                    version = _get_r_version(entry / "bin" / "R")
                    installed_r.append({
                        "home_path": entry,
                        "executable_path": entry / "bin" / "R",
                        "version": version,
                        "active": True,
                    })
        except (FileNotFoundError,
                subprocess.CalledProcessError,
                KeyError):
            logger.exception("Failed option")

    return installed_r


def _get_plist_version(path: pathlib.Path) -> str:
    """Extract the current version from the macos plist file"""
    tree = ElementTree.parse(path)
    root = tree.getroot()
    if root.tag != "plist":
        raise KeyError("Invalid plist file")

    dict_ = root[0]
    if dict_.tag != "dict":
        raise KeyError("Invalid plist file")

    found_version = False
    for entry in dict_:
        if found_version:
            if entry.tag == "string":
                if entry.text is None:
                    raise KeyError("Invalid plist file")
                return entry.text
            else:
                raise KeyError("Invalid plist file")
        if entry.tag == "key" and entry.text == "CFBundleVersion":
            found_version = True

    raise KeyError("Invalid plist file")


def _get_r_version(path: pathlib.Path) -> str:
    """Extract the current version from the run of the R executable"""

    output = subprocess.check_output([path, "--version"], encoding="utf-8")

    m = re.match(r"R version\s*(\d\.\d\.\d)", output)
    if m is None:
        raise KeyError("Unable to find version in R output")

    version = m.group(1)
    return version


def _find_highest_active_version() -> Optional[Dict]:

    active_homes = filter(lambda x: x["active"] is True,
                          find_all_installed_r_homes())

    try:
        highest_version = sorted(
            active_homes,
            key=lambda x: [int(i) for i in x["version"].split(".")] +
                          [x["executable_path"]],
            reverse=True
        )[0]
        return highest_version
    except IndexError:
        return None


def _find_active_r_version(r_version: str) -> Optional[Dict]:
    active_homes = filter(
        lambda x: x["active"] is True and x["version"] == r_version,
        find_all_installed_r_homes()
    )

    try:
        active_version = sorted(
            active_homes,
            key=lambda x: x["executable_path"],
            reverse=True
        )[0]
        return active_version
    except IndexError:
        return None
