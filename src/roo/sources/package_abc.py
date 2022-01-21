import abc
from typing import List

from roo.parsers.description import Dependency


class PackageABC(abc.ABC):
    """Represents a package on a source"""

    @property
    @abc.abstractmethod
    def versioned_name(self) -> str:
        """The name of the package as obtained by its filename,
        including its version but excluding the extensions.
        e.g. stringi_1.2.3
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The plain name of the package. e.g. stringi
        """

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """The version of the package from its filename. e.g. 1.2.3"""

    @property
    @abc.abstractmethod
    def dependencies(self) -> List[Dependency]:
        """Returns the list of dependencies the package has.
        If the file is not locally downloaded, this call will download
        the package."""

    @property
    @abc.abstractmethod
    def r_constraint(self) -> List[str]:
        """Returns the constraints on the R version"""
