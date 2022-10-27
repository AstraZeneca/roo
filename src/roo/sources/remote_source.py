import logging
import pathlib
import tempfile
from typing import Union, List, Dict, Optional, Any, cast
from urllib.parse import urljoin

from ..parsers.description import Description
from bs4 import BeautifulSoup

from ..network import session_with_proxy
from .source_package import SourcePackage
from .exceptions import PackageNotFoundError
from .source_abc import SourceABC

logger = logging.getLogger(__file__)


class RemoteSource(SourceABC):
    """Provides access to a remote source, such as CRAN or CRAN-like.
    Supports both CRAN and Artifactory layouts transparently.
    """

    def __init__(self, name: str, url: str,
                 proxy: Optional[Union[str, bool]] = None,
                 priority: int = 0):
        super().__init__(name, url, priority)
        self.proxy = proxy
        self._session = session_with_proxy(self.proxy)

        # Instead of parsing the HTML file every time, we download
        # everything once and store it here, parsed. The key '' is the contrib
        # list. The key with a given package name is the subdir in the archive
        # associated to that.
        self._index_cache: Dict[str, List[SourcePackage]] = {}
        self._packages: Dict[str, List[SourcePackage]] = {}

    @property
    def location(self) -> str:
        return self.url

    @property
    def archive_url(self) -> str:
        return urljoin(self.contrib_url, "Archive/")

    @property
    def contrib_url(self) -> str:
        return urljoin(self.url, "src/contrib/")

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
        Finds all available versions of a package

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
        Downloads a package from the source and stores it in the cache.
        This method is called by Package to download itself.
        It always performs download, even if the package is already in
        cache.

        package will be modified after this operation has taken place.

        Args:
            package: the package to download.

        """
        logger.info(f"Downloading package {package.url}")
        res = self._session.get(package.url)
        res.raise_for_status()
        with tempfile.TemporaryDirectory() as tmp:
            tmppath = pathlib.Path(tmp) / package.filename
            with open(tmppath, "wb") as f:
                f.write(res.content)

            pkg_file_path = self._cache.add_package_file(
                package.name, package.version, tmppath)

        package.local_path = pkg_file_path
        description_file = self._cache.get_package_description_file(
            package.name, package.version)

        package.description = Description.parse(description_file)

    def _active_packages(self) -> list:
        """
        Returns the active packages, those who are in the index.

        Returns: the list of packages

        """
        packages = self._index_cache.get('')
        if packages is not None:
            return packages

        logger.info("Downloading contrib url from source %s", self.url)
        res = self._session.get(self.contrib_url)
        res.raise_for_status()

        index_content = res.text

        data = BeautifulSoup(index_content, features="html.parser")

        packages = []
        for entry in data.find_all("a"):
            if _is_package_entry(entry):
                pkg = SourcePackage(
                    filename=entry["href"],
                    active=True,
                    url=urljoin(self.contrib_url, entry["href"]),
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

        subdir_url = urljoin(self.archive_url, package_name+'/')

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

        pkgfiles, dirs = _get_pkgfiles_and_dirs_at_url(self._session,
                                                       subdir_url)

        # This gets the CRAN format
        for filename in pkgfiles:
            if filename in packages:
                continue

            pkg = SourcePackage(
                filename=filename,
                active=False,
                url=urljoin(subdir_url, filename),
                source=self
            )
            if self._cache.has_package_file(pkg.name, pkg.version):
                pkg.local_path = self._cache.get_package_file(
                    pkg.name, pkg.version
                )
                description_file = self._cache.get_package_description_file(
                    pkg.name, pkg.version)
                pkg.description = Description.parse(description_file)
            packages[filename] = pkg

        # This gets the Artifactory format
        for dir_ in dirs:
            # all these directories are in principle versions.
            # We do not recurse deeper because we don't want to start long
            # running fetching, and there's no need for it.
            versioned_subdir_url = urljoin(subdir_url, dir_)
            pkgfiles, _ = _get_pkgfiles_and_dirs_at_url(
                self._session, versioned_subdir_url)

            for filename in pkgfiles:
                if filename in packages:
                    continue

                pkg = SourcePackage(
                    filename=filename,
                    active=False,
                    url=urljoin(versioned_subdir_url, filename),
                    source=self
                )
                if self._cache.has_package_file(pkg.name, pkg.version):
                    pkg.local_path = self._cache.get_package_file(
                        pkg.name, pkg.version
                    )
                    desc_file = self._cache.get_package_description_file(
                        pkg.name, pkg.version)
                    pkg.description = Description.parse(desc_file)
                packages[filename] = pkg

        self._index_cache[package_name] = list(packages.values())
        return self._index_cache[package_name]


def _is_package_entry(entry: Any) -> bool:
    """Returns True if the html entry describes a package."""
    href = entry["href"]
    return cast(bool, (
        href.endswith("gz")
        and href == entry.string
        and href != "PACKAGES.gz"
    ))


def _is_dir_entry(entry: Any) -> bool:
    """Returns true if the html entry refers to a directory."""
    href = entry["href"]
    return cast(bool, (href.endswith("/") and href == entry.string))


def _get_pkgfiles_and_dirs_at_url(session: Any, url: str) -> tuple:
    """Utility function to get the tar.gz files and the directories
    at a given URL.
    """
    res = session.get(url)
    if res.status_code == 404:
        return [], []
    res.raise_for_status()
    index_content = res.text

    data = BeautifulSoup(index_content, features="html.parser")

    packages, dirs = [], []

    for entry in data.find_all("a"):
        if _is_package_entry(entry):
            packages.append(entry["href"])
        elif _is_dir_entry(entry):
            dirs.append(entry["href"])

    return packages, dirs
