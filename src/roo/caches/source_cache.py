import string
import random
import tarfile
import hashlib
import shutil
import pathlib
import atomicwrites
from urllib.parse import urlparse
from typing import Union, Optional


class SourceCache:
    """
    Local cache for source packages. These packages can be either
    originate from downloaded sources, or from a local director.

    Note: even for local packages, we always copy the package to the cache.
    The reason is that the package may be on a network drive that may
    become unavailable. Disk space is cheap nowadays anyway.
    We could optimise local access by using a symbolic link, but we still
    need to extract the DESCRIPTION file in the cache anyway.
    """

    def __init__(self,
                 source_url: str,
                 root_dir: Optional[pathlib.Path] = None):
        """Provide access to the cache section for a given source url
        (if remote), or local path (if local). In any case, we take a string.
        """
        if root_dir is None:
            root_dir = pathlib.Path("~/.roo/cache").expanduser()

        self.root_dir = root_dir
        self.source_url = source_url
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # all computed directories
    @property
    def base_dir(self) -> pathlib.Path:
        """
        Returns the base directory for the cache.

        Returns: The base directory for the cache of that source
        """
        url = urlparse(self.source_url)
        if url.netloc == "":
            source_location = pathlib.Path("local")
        else:
            source_location = pathlib.Path("remote") / url.netloc
        return self.root_dir / "source" / source_location / \
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

                try:
                    with atomicwrites.atomic_write(
                            description_path, mode="wb") as f:
                        f.write(description.read())
                except FileExistsError:
                    # If the file already exists at this point, it's
                    # likely that a concurrent process created it as well,
                    # so we just keep going.
                    pass
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

        if pkg_path.exists():
            return pkg_path

        letters = string.ascii_lowercase
        append = ''.join(random.choice(letters) for i in range(10))

        partial_pkg_path = (
            self.package_dir(package_name) /
            (f"{package_name}_{package_version}." + append)
        )

        # first copy it locally so that we guarantee that atomic operations.
        # are not compromised by different filesystems.
        # If both processes do the copy it's not a problem because they
        # have different append strings.
        shutil.copy(path, partial_pkg_path)

        # Then perform the atomic move. Only one will succeed, the other
        # will get a FileExistError and we'll keep going.
        try:
            atomicwrites.move_atomic(str(partial_pkg_path), str(pkg_path))
        except FileExistsError:
            pass

        return pkg_path
