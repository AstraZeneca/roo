from __future__ import annotations
from typing import List, TYPE_CHECKING, Union, Dict
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
    def all_sources(self) -> List[SourceABC]:
        """
        Return a list of the available sources.
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

        # Little bit of gymnastic here.
        #
        # First we want to use the priority to search the package.
        # If a package is found on a given priority layer, we won't continue
        # to lower priorities, _even_ if there are higher versions in the
        # lower priority sources. This is to prevent "takeover" from
        # external sources of internal packages.
        # Additionally, at a given layer of priority, we want to keep the
        # order of the packages with respect to the source, because if the
        # same package version is found in two or more sources, we want to
        # honor the order and install from the first source, not the second.

        # So, first we get all the packages that respect the constraint.
        # We start from the highest priority and descend. Note that
        # sources_by_priority returns from lowest to highest.
        for sources_at_priority in reversed(self._sources_by_priority()):
            available_packages: List[SourcePackage] = []
            for source in sources_at_priority:
                packages = source.find_package_versions(name)
                logger.info(
                    f"Source {source.name} with priority {source.priority} "
                    f"has package versions {[p.version for p in packages]}"
                )
                packages = [
                    package for package in packages
                    if constraint.allows(Version.parse(package.version))
                ]
                available_packages.extend(packages)

            if len(available_packages) == 0:
                # Found not a single one? Try next priority
                continue

            # Then find out the most recent version of the ones available.
            highest_version = sorted([
                Version.parse(package.version)
                for package in available_packages])[-1]

            # and filter away the packages that are too low.
            # Note that we could have the same package many times, once
            # per each source. However, the sorting is stable so we get
            # the first source always.
            available_packages = [
                package for package in available_packages
                if Version.parse(package.version) == highest_version
            ]

            # and finally, return the one from the first source
            return available_packages[0]

        # We tried all priorities and found nothing.
        raise PackageNotFoundError(f"{name} {constraint}")

    def _sources_by_priority(self) -> List[List[SourceABC]]:
        """Returns the sources grouped together by priority, as a list
        of lists. Groups are ordered from the lowest to the highest priority.
        inside each group, they preserve the order of addition.
        """
        d: Dict[int, List[SourceABC]] = {}
        for source in self.all_sources:
            sources_for_priority = d.setdefault(source.priority, [])
            sources_for_priority.append(source)

        ret = []
        for idx in sorted(d.keys()):
            ret.append(d[idx])

        return ret


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
