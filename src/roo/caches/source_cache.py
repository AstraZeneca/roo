import tarfile
import hashlib
import shutil
import pathlib
import atomicwrites
from urllib.parse import urlparse
from typing import Union


class SourceCache:
    """
    Local cache for sources content.
    Due to the nature of the CRAN sources not exposing an Etag, we cannot
    store things with Cache-Control: no-cache, which is the majority of
    index data. We can however cache the downloaded packages.
    """

    def __init__(self, source_url: str):
        self.root_dir = pathlib.Path("~/.roo/cache").expanduser()
        self.source_url = source_url
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # all computed directories
    @property
    def base_dir(self) -> pathlib.Path:
        """
        Returns the base directory for the cache

        Returns: The base directory for the cache of that source
        """
        url = urlparse(self.source_url)
        return self.root_dir / "source" / url.netloc / \
            hashlib.sha256(url.path.encode("utf-8")).hexdigest()

    def package_dir(self, package_name: str) -> pathlib.Path:
        path = self.base_dir / package_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def package_meta_dir(self,
                         package_name: str,
                         package_version: str) -> pathlib.Path:
        """
        Returns the meta directory for a given package version

        Args:
            package_name: the package name
            package_version: the package version

        Returns:
            The path to the package meta directory
        """
        package_dir = self.package_dir(package_name)
        path = package_dir / f"{package_name}_{package_version}.meta-info"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_package_file(self,
                         package_name: str,
                         package_version: str) -> Union[pathlib.Path, None]:
        """
        Gets the path to the package if the package is already in cache.
        If not, return None.

        Args:
            package_name: the name of the package
            package_version: the version of the package

        Returns: the path of the package .tar.gz or None if not found.

        """
        pkg_path = (
            self.package_dir(package_name) /
            f"{package_name}_{package_version}.tar.gz")

        if pkg_path.exists():
            return pkg_path

        return None

    def get_package_description_file(
            self,
            package_name: str,
            package_version: str) -> Union[pathlib.Path, None]:
        """
        Gets the package DESCRIPTION file path.

        Args:
            package_name: the package name
            package_version: the package version

        Returns: the path to the description file if available, otherwise None

        """
        meta_dir = self.package_meta_dir(package_name, package_version)

        description_path = meta_dir / "DESCRIPTION"
        if description_path.exists():
            return description_path

        pkg_path = (
            self.package_dir(package_name) /
            f"{package_name}_{package_version}.tar.gz"
        )

        try:
            with tarfile.open(pkg_path) as tar:
                names = tar.getnames()

                # Gets the shortest member that ends with DESCRIPTION.
                # This way we exclude DESCRIPTION files in subdirectories.
                try:
                    desc_name = sorted([
                        x for x in names
                        if x.endswith("DESCRIPTION")], key=len)[0]
                except IndexError:
                    raise ValueError("The package does not have a DESCRIPTION "
                                     "file")

                description = tar.extractfile(desc_name)
                if description is None:
                    raise ValueError("Unable to unpack DESCRIPTION file")

                with atomicwrites.atomic_write(
                        description_path, mode="wb") as f:
                    f.write(description.read())
        except FileNotFoundError:
            return None

        return description_path

    def has_package_file(self,
                         package_name: str,
                         package_version: str) -> bool:
        """Returns true if the package file is present.
        """
        return self.get_package_file(package_name, package_version) is not None

    def add_package_file(self,
                         package_name: str,
                         package_version: str,
                         path: pathlib.Path) -> pathlib.Path:
        """
        Adds a package from a given path to the appropriate place in the cache.

        Args:
            package_name: the name of the package
            package_version: the version of the package
            path: the path of the file to import

        Returns: the path of the added package

        """
        pkg_path = (
            self.package_dir(package_name) /
            f"{package_name}_{package_version}.tar.gz"
        )

        meta_dir = self.package_meta_dir(package_name, package_version)
        description_path = meta_dir / "DESCRIPTION"
        if pkg_path.exists() and description_path.exists():
            return pkg_path

        partial_pkg_path = (
            self.package_dir(package_name) /
            f"{package_name}_{package_version}.part"
        )

        shutil.copy(path, partial_pkg_path)
        atomicwrites.move_atomic(str(partial_pkg_path), str(pkg_path))

        return pkg_path
