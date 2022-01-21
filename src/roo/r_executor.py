from __future__ import annotations
import pathlib
import re
import subprocess
import logging
import typing

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .environment import Environment


logger = logging.getLogger(__file__)


class ExecutorError(Exception):
    """Raised when the executor cannot perform its operation."""


class RExecutorBase:
    """Interface to R execution in a given environment, or to an
    executable by path detached from an environment"""

    def __init__(self, quiet: bool = False, use_vanilla: bool = False):
        self.quiet = quiet
        self.use_vanilla = use_vanilla

    def install(self, package_path: pathlib.Path) -> None:
        """
        Calls R CMD INSTALL on a tar.gz or dir package

        Args:
            package_path: the path of the package .tar.gz to install
        """
        # QSOL-305. Apparently subprocess on windows does not like pathlib.Path
        # objects, so we need to convert them to strings.

        logger.info(f"Installing {package_path}")

        command = ["CMD", "INSTALL"]

        command.extend(self._install_options())
        command.append(str(package_path))

        try:
            self._run_r(command)
        except subprocess.CalledProcessError:
            raise ExecutorError(
                f"Unable to install package {package_path}. "
                f"Execution of command failed"
            )

    def remove(self, package_name: str) -> None:
        """
        Calls R CMD REMOVE on a specific package name.

        Args:
            package_name: the name of the package
        """

        logger.info(f"Removing {package_name}")

        command = ["CMD", "REMOVE"]

        command.extend(self._remove_options())
        command.append(package_name)

        try:
            self._run_r(command)
        except subprocess.CalledProcessError:
            raise ExecutorError(
                f"Unable to remove package {package_name}. "
                f"Execution of command failed.")

    @property
    def version_info(self) -> typing.Dict[str, str]:
        """
        Returns the version info as a dictionary with two keys::

        - version: the version of the R executable
        - platform: the platform of the R executable

        """
        command = [str(self.r_executable_path), "--version"]

        try:
            out = subprocess.check_output(
                command,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                cwd=self._run_cwd()
            )
        except subprocess.CalledProcessError:
            raise ExecutorError(
                "Unable to retrieve version info. "
                "Check your R --version output"
            )

        m = re.search(r"R version\s(.+?)\s", out)
        if m:
            version = m.group(1).strip()
        else:
            raise ExecutorError(
                "Unable to obtain version info. Check your R --version output")

        m = re.search(r"Platform:\s(.+?)\s", out)
        if m:
            platform = m.group(1).strip()
        else:
            raise ExecutorError(
                "Unable to obtain platform info. "
                "Check your R --version output"
            )

        if len(version) == 0 or len(platform) == 0:
            raise ExecutorError(
                "Empty version or platform info found. "
                "Check your R --version output and "
                "send it as a bug report."
            )

        return {"version": version, "platform": platform}

    @property
    def version(self) -> str:
        return self.version_info["version"]

    @property
    def r_executable_path(self) -> pathlib.Path:
        raise NotImplementedError()

    def _remove_options(self):
        raise NotImplementedError()

    def _install_options(self) -> list:
        if self.use_vanilla:
            return ["--use-vanilla"]
        return []

    def _run_cwd(self):
        raise NotImplementedError()

    def _run_r(self, command: list):
        run_cwd = self._run_cwd()
        logger.info(
            f"Executing {self.r_executable_path} {command} with cwd={run_cwd}")
        stdout: Any
        stderr: Any
        if self.quiet:
            stdout = subprocess.DEVNULL
            stderr = subprocess.DEVNULL
        else:
            stdout = None
            stderr = None

        try:
            subprocess.check_call(
                [str(self.r_executable_path)] + command,
                stdout=stdout, stderr=stderr, cwd=run_cwd)
        except FileNotFoundError:
            raise ExecutorError(
                f"Unable to execute {self.r_executable_path}. "
                f"Does the R executable exist?")


class RUnboundExecutor(RExecutorBase):
    """
    Represents an executor that is not bound to a specific
    environment.
    """

    def __init__(self, r_executable_path: pathlib.Path, **kwargs):
        self._r_executable_path = r_executable_path
        super().__init__(**kwargs)

    @property
    def r_executable_path(self) -> pathlib.Path:
        return self._r_executable_path

    def _remove_options(self) -> list:
        return []

    def _run_cwd(self) -> pathlib.Path:
        return pathlib.Path.cwd()


class RBoundExecutor(RExecutorBase):
    """
    Interface to R execution in a given environment.
    """

    def __init__(self, environment: Environment, **kwargs):
        self.environment = environment
        super().__init__(**kwargs)

    def _install_options(self) -> list:
        options = super()._install_options()
        options.extend(["-l", str(self.environment.lib_reldir)])
        return options

    def _remove_options(self) -> list:
        return ["-l", str(self.environment.lib_reldir)]

    @property
    def r_executable_path(self) -> pathlib.Path:
        return self.environment.r_executable_path

    def _run_cwd(self) -> pathlib.Path:
        return self.environment.base_dir
