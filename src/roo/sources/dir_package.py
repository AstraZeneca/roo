import pathlib
from typing import List

from roo.sources.package_abc import PackageABC

from ..parsers.description import Description, Dependency


class DirPackage(PackageABC):
    """Represents a package in a local directory"""

    def __init__(self, dir_path: pathlib.Path):
        """
        Initialises the object.

        Args:
            dir_path: the path where to find the package
        """

        self.dir_path = dir_path
        self.description = Description.parse(dir_path / "DESCRIPTION")

    @property
    def versioned_name(self) -> str:
        """The name of the package including its version.
        e.g. stringi_1.2.3
        """
        return self.description.package + "_" + self.description.version

    @property
    def name(self) -> str:
        """The plain name of the package. e.g. stringi"""
        return self.description.package

    @property
    def version(self) -> str:
        """The version of the package from its filename. e.g. 1.2.3"""
        return self.description.version

    @property
    def dependencies(self) -> List[Dependency]:
        """Returns the list of description dependencies the package has."""
        return self.description.dependencies

    @property
    def r_constraint(self) -> List[str]:
        return self.description.r_constraint
