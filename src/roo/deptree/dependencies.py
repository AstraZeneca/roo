"""Node objects to represent the resolution tree.
This tree is discovered progressively and at any moment
it is composed of resolved and unresolved dependencies until
everything is fully traversed and resolved.

This tree is generally serialised as a lock file.
"""
from __future__ import annotations
import dataclasses
from typing import List, Union, Optional

from ..semver import VersionConstraint
from ..sources.source_package import SourcePackage


@dataclasses.dataclass
class RootDependency:
    """Represents the top of the tree of dependencies.
    It has no name or category."""
    # its subdependencies, which can only be structural
    dependencies: List[StructuralDependency]


@dataclasses.dataclass
class ResolvedDependency:
    """Base class for all resolved dependencies"""
    # The dependency name
    name: str
    # the categories it belongs to.
    categories: List[str]
    # its subdependencies, which can only be structural
    dependencies: List[StructuralDependency]

    def add_categories_recursive(self, categories: List[str]):
        """Adds a category to the dependency, and also traverse
        the tree to add the same category to all its subdependencies"""
        self.categories = list(set(self.categories + categories))

        for subdep in self.dependencies:
            if isinstance(subdep, ResolvedDependency):
                subdep.add_categories_recursive(categories)
            elif isinstance(subdep, UnresolvedDependency):
                subdep.categories = list(set(subdep.categories + categories))
            else:
                raise TypeError(f"Unexpected type for {subdep}")


@dataclasses.dataclass
class ResolvedSourceDependency(ResolvedDependency):
    """Represents a dependency that is resolved by a source such as CRAN"""
    # The package that this dependency uses for resolution
    package: SourcePackage

    # The constraint on the R version this dependency has
    r_constraint: VersionConstraint


@dataclasses.dataclass
class ResolvedVCSDependency(ResolvedDependency):
    """Represents a dependency that is resolved by a Version control system"""
    # The VCS type (for now only git)
    vcs_type: str
    # The url of the VCS endpoint
    url: str
    # the reference to checkout. If absent, just check out without
    # switching to a particular ref.
    ref: Optional[str]


@dataclasses.dataclass
class ResolvedCoreDependency(ResolvedDependency):
    """Represents a core dependency that is resolved by R itself"""


@dataclasses.dataclass
class UnresolvedDependency:
    """
    Represents a dependency that is currently still unresolved.
    """
    name: str
    categories: List[str]


@dataclasses.dataclass
class UnresolvedConstrainedDependency(UnresolvedDependency):
    """represents an unresolved dependency that is described by a name
    and a constraint"""
    constraint: VersionConstraint


@dataclasses.dataclass
class UnresolvedVCSDependency(UnresolvedDependency):
    """Represents an unresolved dependency pointing at a VCS resource"""
    vcs_type: str
    url: str
    ref: Optional[str]


# StructuralDependency is a type for any dependency, resolved or unresolved,
# that is not the root dependency
StructuralDependency = Union[ResolvedDependency, UnresolvedDependency]
AnyDependency = Union[RootDependency, ResolvedDependency, UnresolvedDependency]
