from __future__ import annotations
from typing import List, TYPE_CHECKING, Union
from collections import OrderedDict
import logging

from .source_package import SourcePackage
from ..semver import VersionConstraint, Version
from .exceptions import PackageNotFoundError
from .source_abc import SourceABC
from .remote_source import RemoteSource

if TYPE_CHECKING:
    from ..parsers.lock import Source as LockSource
    from ..parsers.rproject import Source as RProjectSource


logger = logging.getLogger(__name__)


class SourceGroup:
    """
    Represents a more flexible storage for the set of sources.
    """

    def __init__(self):
        self.sources: OrderedDict[str, SourceABC] = OrderedDict()

    def add_source(self, source: SourceABC):
        """
        Adds a source to the group
        """
        if source.name in self.sources:
            raise ValueError("Source already present")

        self.sources[source.name] = source

    def source_by_name(self, name: str) -> SourceABC:
        """Return the source if found. Otherwise raises KeyError"""
        return self.sources[name]

    @property
    def all_sources(self):
        """
        Return a list of the available sources. The order
        depends on the priority
        """
        return list(self.sources.values())

    def find_most_recent_package(self,
                                 name: str,
                                 constraint: VersionConstraint
                                 ) -> SourcePackage:
        """Find the most recent package satisfying a given constraint
        across all sources"""

        logger.info(f"Finding most recent package for {name} "
                    f"with constraint {constraint}")

        # Little bit of gymnastic here. We need to keep the order of the
        # packages with respect to the source, because if the same package
        # version is found in two or more sources, we want to honor the order
        # and install from the first source, not the second.
        # So, first we get all the packages that respect the constraint
        available_packages: List[SourcePackage] = []
        for source in self.all_sources:
            packages = source.find_package_versions(name)
            logger.info(f"source {source.name} has package versions "
                        f"{[p.version for p in packages]}")
            packages = [
                package for package in packages
                if constraint.allows(Version.parse(package.version))
            ]
            available_packages.extend(packages)

        # Found not a single one? bail out.
        if len(available_packages) == 0:
            raise PackageNotFoundError(f"{name} {constraint}")

        # Then find out the most recent version of the ones available.
        highest_version = sorted([
            Version.parse(package.version)
            for package in available_packages])[-1]

        # and filter away the packages that are too low.
        # Note that we could have the same package many times, once
        # per each source. However, the sorting is stable so we get the first
        # source always.
        available_packages = [
            package for package in available_packages
            if Version.parse(package.version) == highest_version
        ]

        # and finally, return the one from the first source
        return available_packages[0]


def create_source_group_from_config_list(
        config_list: Union[List[LockSource], List[RProjectSource]]
) -> SourceGroup:
    """
    Create the source group from the configuration settings
    obtained by the config files.
    """
    group = SourceGroup()
    for config in config_list:
        group.add_source(RemoteSource(name=config.name,
                                      url=config.url,
                                      proxy=config.proxy))

    return group
