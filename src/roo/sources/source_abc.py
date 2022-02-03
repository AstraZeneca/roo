from abc import ABC, abstractmethod
from typing import List

from roo.caches.source_cache import SourceCache

from .source_package import SourcePackage


class SourceABC(ABC):
    """Abstract base class of a source of packages"""

    def __init__(self, name, url, priority):
        self.name = name
        self.url = url
        self.priority = priority
        self._cache = SourceCache(self.url)

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
    def retrieve_package_to_cache(self, package: SourcePackage):
        """
        Retrieve a package from the source.
        This method is called by Package to download itself.
        It always performs retrieval, even if the package is already in
        cache.

        package will be modified after this operation has taken place.

        Args:
            package: the package to retrieve.

        """
