import logging
import pathlib
from typing import List, Dict

from ..parsers.description import Description

from .source_package import SourcePackage
from .exceptions import PackageNotFoundError
from .source_abc import SourceABC

logger = logging.getLogger(__file__)


class LocalSource(SourceABC):
    """Provides access to a local source, that is, a layout such as CRAN
    on a local disk.
    """

    def __init__(self, name: str, path: pathlib.Path, priority: int = 0):
        super().__init__(name, str(path), priority)

        # Instead of parsing the HTML file every time, we download
        # everything once and store it here, parsed. The key '' is the contrib
        # list. The key with a given package name is the subdir in the archive
        # associated to that.
        self._packages: Dict[str, List[SourcePackage]] = {}
        self._index_cache: Dict[str, List[SourcePackage]] = {}

    @property
    def archive_path(self) -> pathlib.Path:
        return self.contrib_path / "Archive"

    @property
    def contrib_path(self) -> pathlib.Path:
        return pathlib.Path(self.url) / "src" / "contrib"

    def find_package(self, name: str, version: str) -> SourcePackage:
        """
        Finds a package by name and version

        Args:
            name: name of the package
            version: version of the package

        Returns: the package object

        Raises: PackageNotFoundError

        """
        logger.info(f"Finding package {name} {version}")
        packages = self.find_package_versions(name)
        try:
            return [x for x in packages if x.version == version][0]
        except IndexError:
            raise PackageNotFoundError(f"{name} {version}")

    def find_package_versions(self, name: str) -> List[SourcePackage]:
        """
        Finds all available versions of a package. Note that packages
        are returned in arbitrary order.

        Args:
            name: the name of the package

        Returns: a list of all packages with that name.

        """
        logger.info(f"Finding packages for {name}")
        if name not in self._packages:
            all_packages = self._active_packages()
            packages = [x for x in all_packages if x.name == name]
            archived_packages = self._archived_packages(name)

            self._packages[name] = packages + archived_packages

        return self._packages[name]

    def retrieve_package_to_cache(self, package: SourcePackage):
        """
        """
        pkg_file_path = self._cache.add_package_file(
            package.name, package.version, pathlib.Path(package.url))

        package.local_path = pkg_file_path
        description_file = self._cache.get_package_description_file(
            package.name, package.version)

        package.description = Description.parse(description_file)

    def _active_packages(self) -> list:
        """
        Returns the active packages, those who are in the index.

        Returns: the list of packages

        """
        # blank entry is reserved for active packages.
        packages = self._index_cache.get('')
        if packages is not None:
            return packages

        packages = []

        if not self.contrib_path.exists():
            return packages

        for entry in self.contrib_path.iterdir():
            if entry == "PACKAGES.gz":
                continue

            elif entry.suffix.endswith("gz"):
                pkg = SourcePackage(
                    filename=str(entry.name),
                    active=True,
                    url=str(self.contrib_path / entry),
                    source=self
                )
                if self._cache.has_package_file(pkg.name, pkg.version):
                    pkg.local_path = self._cache.get_package_file(
                        pkg.name, pkg.version
                    )
                    desc_file = self._cache.get_package_description_file(
                        pkg.name, pkg.version)
                    pkg.description = Description.parse(desc_file)
                packages.append(pkg)

        self._index_cache[''] = packages
        return packages

    def _archived_packages(self, package_name: str) -> list:
        """
        Fetches the appropriate Archive format for a given package name
        and returns the list of available packages.

        Args:
            package_name: the name of the package

        Returns: a list of packages

        """
        cached_packages = self._index_cache.get(package_name)
        if cached_packages is not None:
            return cached_packages

        package_subdir = self.archive_path / package_name

        # Here the parsing needs to consider two cases for the archive:
        #
        # Artifactory style: Archive/package/version/package-version.tar.gz
        # CRAN style: Archive/package/package-version.tar.gz
        #
        # What we do is that we take the list, add all .tar.gz as packages,
        # then with the remaining entries we consider them directory and enter
        # them, adding more tar.gz as we find them. It is not recursive.
        # Just one level.
        # If the same package is present twice, we take the CRAN style package
        # first and discard the rest.

        # use a dict so we can keep track of the names and skip if we find dups
        packages = {}

        pkgfiles, dirs = _get_pkgfiles_and_dirs_at_path(package_subdir)

        # This gets the CRAN format
        for filepath in pkgfiles:
            if filepath.name in packages:
                continue

            pkg = SourcePackage(
                filename=filepath.name,
                active=False,
                url=str(filepath),
                source=self
            )
            if self._cache.has_package_file(pkg.name, pkg.version):
                pkg.local_path = self._cache.get_package_file(
                    pkg.name, pkg.version
                )
                description_file = self._cache.get_package_description_file(
                    pkg.name, pkg.version)
                pkg.description = Description.parse(description_file)
            packages[filepath.name] = pkg

        # This gets the Artifactory format
        for dir_ in dirs:
            # all these directories are in principle versions.
            # We do not recurse deeper because we don't want to start long
            # running fetching, and there's no need for it.
            versioned_subdir = package_subdir / dir_
            pkgfiles, _ = _get_pkgfiles_and_dirs_at_path(versioned_subdir)

            for filepath in pkgfiles:
                if filepath.name in packages:
                    continue

                pkg = SourcePackage(
                    filename=filepath.name,
                    active=False,
                    url=str(filepath),
                    source=self
                )
                if self._cache.has_package_file(pkg.name, pkg.version):
                    pkg.local_path = self._cache.get_package_file(
                        pkg.name, pkg.version
                    )
                    desc_file = self._cache.get_package_description_file(
                        pkg.name, pkg.version)
                    pkg.description = Description.parse(desc_file)
                packages[filepath.name] = pkg

        self._index_cache[package_name] = list(packages.values())
        return self._index_cache[package_name]


def _get_pkgfiles_and_dirs_at_path(path: pathlib.Path) -> tuple:
    """Utility function to get the tar.gz files and the directories
    at a given URL.
    """
    packages: List[pathlib.Path] = []
    dirs: List[pathlib.Path] = []

    if not path.exists():
        return packages, dirs

    for entry in path.iterdir():
        if entry.name == "PACKAGES.gz":
            continue
        elif entry.suffix.endswith("gz"):
            packages.append(entry)
        elif entry.is_dir():
            dirs.append(entry)

    return packages, dirs
