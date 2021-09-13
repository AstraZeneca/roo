from abc import ABC, abstractmethod
from typing import List

from .source_package import SourcePackage


class SourceABC(ABC):
    """Abstract base class of a source of packages"""

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def find_package(self,
                     name: str,
                     version: str) -> SourcePackage:
        """
        Finds a package by name and version, or None if not available.

        Args:
            name: name of the package
            version: version of the package

        Returns: the package object

        Raises:
            PackageNotFoundError

        """

    @abstractmethod
    def find_package_versions(self, name: str) -> List[SourcePackage]:
        """
        Finds all available versions of a package

        Args:
            name: the name of the package

        Returns: a list of all packages with that name.

        """

    @abstractmethod
    def download_package(self, package: SourcePackage):
        """
        Downloads a package from the source.
        This method is called by Package to download itself.
        It always performs download, even if the package is already in
        cache.

        package will be modified after this operation has taken place.

        Args:
            package: the package to download.

        """
