import logging
import tarfile
import shutil
import pathlib
import typing
import os
from typing import List, Tuple, Optional
import atomicwrites


logger = logging.getLogger(__name__)


class BuildCache:
    """
    Local cache for built packages.
    """

    def __init__(self,
                 r_version: str,
                 platform: str,
                 root_dir: typing.Optional[pathlib.Path] = None):

        if root_dir is None:
            root_dir = pathlib.Path("~/.roo/cache").expanduser()

        self.root_dir = root_dir
        self.r_version = r_version
        self.platform = platform

    # all computed directories
    @property
    def base_dir(self) -> pathlib.Path:
        """
        Returns the base directory for the cache.

        Returns: The base directory for the cache

        """
        path = self.root_dir / "build" / self.r_version / self.platform
        path.mkdir(parents=True, exist_ok=True)
        return path

    def has_build(self, package_name: str, package_version: str) -> bool:
        """
        Check if the build is available in cache.

        Args:
            package_name: the name of the package
            package_version: the version of the package

        Returns: true if available. False otherwise.

        """
        pkg_path = self._package_filename(package_name, package_version)

        return pkg_path.exists()

    def add_build(self,
                  package_name: str,
                  package_version: str,
                  path: pathlib.Path) -> pathlib.Path:
        """
        Adds a build directory and store it in the cache.

        Args:
            package_name: the name of the package
            package_version: the version of the package
            path: the path of the file to import

        Returns: the path of the added package

        """
        logger.info(f"Adding {path} to {package_name} {package_version}")
        pkg_path = self._package_filename(package_name, package_version)

        try:
            with atomicwrites.atomic_write(
                    pkg_path, mode="wb", overwrite=True) as f:
                with tarfile.open(fileobj=f, mode="w:gz") as targz:
                    targz.add(str(path), arcname=".")
        except FileExistsError:
            # A concurrent process has built the same thing and got there
            # first.
            pass

        return pkg_path

    def restore_build(self,
                      package_name: str,
                      package_version: str,
                      destination: pathlib.Path):
        """
        Restores the given build to a given destination path.

        Args:
            package_name: the package name
            package_version: the package version
            destination: where the restored build will have to go

        Raises:
            FileNotFoundError if the cache does not contain the build.

        """

        logger.info(
            f"Restoring cached installation "
            f"{package_name} {package_version} to {destination}")

        pkg_path = self._package_filename(package_name, package_version)

        shutil.rmtree(destination, ignore_errors=True)

        try:
            with tarfile.open(pkg_path, "r:gz") as targz:
                targz.extractall(str(destination))
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Unable to restore build {package_name} {package_version} "
                f"for R version {self.r_version}"
            ) from None

    def clear_build(
            self, package_name: str, package_version: Optional[str] = None):
        """
        Clears the given build for package identified by package_name and
        package_version
        """
        entries_to_delete = []
        if package_version is None:
            entries_to_delete = [
                x for x in self.list_builds() if x[0] == package_name
            ]
        else:
            entries_to_delete = [(package_name, package_version)]

        for name, version in entries_to_delete:
            logger.info(
                f"Clearing cached build {name} {version}")

            pkg_path = self._package_filename(name, version)
            if pkg_path.exists():
                pkg_path.unlink()

    def list_builds(self) -> List[Tuple[str, str]]:
        builds = []
        for entry in os.scandir(self.base_dir):
            if entry.name.endswith(".tar.gz"):
                name, version = _split_package_filename(entry.name)
                builds.append((name, version))

        return builds

    def clear(self):
        """Clear all builds and removes the whole cache."""
        shutil.rmtree(self.base_dir)

    def _package_filename(
            self,
            package_name: str,
            package_version: str) -> pathlib.Path:
        """
        Returns the filename of the build.

        Args:
            package_name: the name of the package
            package_version: the version of the package

        Returns: the path of the filename

        """
        return self.base_dir / f"{package_name}_{package_version}.tar.gz"


def _split_package_filename(filename: str) -> Tuple[str, str]:
    return typing.cast(
        Tuple[str, str],
        tuple(filename.rsplit(".", maxsplit=2)[0].rsplit("_", maxsplit=1))
    )


def all_build_caches(root_dir: Optional[pathlib.Path] = None) -> List:
    if root_dir is None:
        root_dir = pathlib.Path("~/.roo/cache").expanduser()

    caches = []
    for r_version in (x for x in (root_dir / "build").iterdir() if x.is_dir()):
        for platform in (x for x in r_version.iterdir() if x.is_dir()):
            caches.append(BuildCache(r_version.name, platform.name, root_dir))

    return caches
