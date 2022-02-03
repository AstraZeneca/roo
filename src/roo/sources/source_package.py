from __future__ import annotations
import os
import pathlib
from typing import List, Optional, TYPE_CHECKING, cast

from roo.sources.package_abc import PackageABC

from ..hashing import sha256path
from ..parsers.description import Description

if TYPE_CHECKING:
    from .source_abc import SourceABC
    from ..parsers.description import Dependency


class SourcePackage(PackageABC):
    """Represents a package on a source"""

    def __init__(self,
                 filename: str,
                 active: bool,
                 url: str,
                 source: SourceABC,
                 expected_hash: Optional[str] = None):
        """
        Initialises the object representing a package on a source.

        Args:
            filename: the filename of the package
            active: if it's the currently active one or is in Archive.
            url: the url of the tar.gz. This can be both a remote url,
                 or a local path (no need for file://)
            source: a backlink to the source this package comes from
        """

        self.filename = filename
        self.active = active
        self.url = url
        self.source = source

        # This is the path in the cache, if the package is present in the
        # cache. Normally set from the source.
        self.local_path: Optional[pathlib.Path] = None
        self.description: Optional[Description] = None
        self.expected_hash = expected_hash

        versioned_name, _ = os.path.splitext(self.filename)
        if versioned_name.endswith(".tar"):
            versioned_name, _ = os.path.splitext(versioned_name)

        self._versioned_name = versioned_name
        self._dependencies = None

        try:
            self._versioned_name.split("_")
        except ValueError:
            raise ValueError(f"versioned name {self._versioned_name} cannot "
                             f"be split in name and version.") from None

    @property
    def versioned_name(self) -> str:
        """The name of the package as obtained by its filename,
        including its version but excluding the extensions.
        e.g. stringi_1.2.3
        """
        return self._versioned_name

    @property
    def name(self) -> str:
        """The plain name of the package. e.g. stringi
        """
        return self.versioned_name.split("_")[0]

    @property
    def version(self) -> str:
        """The version of the package from its filename. e.g. 1.2.3"""
        return self.versioned_name.split("_")[1]

    @property
    def hash(self) -> str:
        """Returns the hash of the file. If the file is not locally
        downloaded, this call will download it first."""
        self.ensure_local()
        return "sha256:"+sha256path(cast(str, self.local_path))

    @property
    def dependencies(self) -> List[Dependency]:
        """Returns the list of dependencies the package has.
        If the file is not locally downloaded, this call will download
        the package."""
        self.ensure_local()
        return cast(Description, self.description).dependencies

    @property
    def r_constraint(self) -> List[str]:
        self.ensure_local()
        return cast(Description, self.description).r_constraint

    def has_local_file(self) -> bool:
        """Returns true if the package has a local file"""
        return self.local_path is not None

    def retrieve(self) -> None:
        """Convenience method to trigger the retrieval of a package
        from its source to the cache.
        This method performs the retrieval regardless if the package is
        already in cache."""
        self.source.retrieve_package_to_cache(self)

    def ensure_local(self) -> None:
        """Ensures that the package has been retrieved locally to cache. If
        it is already present, this function does nothing, otherwise
        it downloads it."""
        if self.has_local_file():
            return

        self.retrieve()

    def hash_match(self):
        """
        Returns true if the expected hash and the downloaded package have
        the same hash.

        Returns: True if the hash and the expected hash are the same,
                 otherwise False.

        Raises

        ValueError if there's no expected hash stored.
        """
        if self.expected_hash is None:
            raise ValueError("Unknown expected hash")

        return self.hash == self.expected_hash

    def __str__(self) -> str:
        return (
            f"SourcePackage(name='{self.name}', version='{self.version}', "
            f"source='{self.source.name}')")
