from __future__ import annotations

from collections import OrderedDict
import logging
from typing import List, cast, Optional, Union

from roo.console import console
from roo.sources.package_abc import PackageABC

from .caches.vcs_store import VCSStore
from .deptree.dependencies import (
    RootDependency, ResolvedDependency,
    ResolvedSourceDependency, ResolvedVCSDependency, ResolvedCoreDependency,
    UnresolvedDependency, UnresolvedConstrainedDependency,
    UnresolvedVCSDependency, StructuralDependency)
from .deptree.traverse import traverse_depth_first_unique
from .semver import VersionConstraint, parse_constraint, Version
from .sources.dir_package import DirPackage
from .sources.exceptions import PackageNotFoundError
from .sources.source_group import SourceGroup
from .sources.vcs import vcs_clone_shallow

logger = logging.getLogger(__file__)


class CannotResolveError(Exception):
    pass


class Resolver:
    def __init__(self, source_group: SourceGroup):
        """The resolver class is what powers the resolution of the tree
        step by step. We feed in a root dependency with the unresolved
        dependencies from the rproject file, and (hopefully) retrieve
        all the tree of resolved dependencies.

        Note that, however, at this stage we don't have any connection
        to a given environment, so one dependency is left unresolved:
        the R version. It will be checked instead at install time.
        In the tree, it's handled as a special dependency, but in the
        lock file it's going to be a special key."""

        self.source_group = source_group
        self.resolved_cache: OrderedDict[str, ResolvedDependency] = \
            OrderedDict()

    def resolve_full_tree(self,
                          root: RootDependency,
                          old_tree: Optional[RootDependency] = None):
        # Keep a cache of what's already been found
        self.resolved_cache.clear()

        if old_tree is not None:
            self._pre_populate_cache(root, old_tree)

        with console().status("Resolving dependencies"):
            self._first_level_resolve(root)

            self._resolve_tree_depth_first(root)

    def _pre_populate_cache(self,
                            root: RootDependency,
                            old_tree: RootDependency):
        """Pre-populate the cache with the old tree.

        If an older tree has been passed, operate in conservative
        mode.
        Conservative mode will try to minimise disruption of version
        by using the already found tree to pre-populate the cache with
        the subdependencies. It will however discard the currently specified
        top level dependencies, otherwise we would be unable to change a
        version in the rproject file
        """
        for dep in traverse_depth_first_unique(old_tree):
            if isinstance(dep, ResolvedDependency):
                self.resolved_cache[dep.name] = dep

        # Now remove the direct dependencies from the cache, so we'll look
        # them up again.
        for dep in root.dependencies:
            del self.resolved_cache[dep.name]

    def _first_level_resolve(self, root: RootDependency) -> None:
        """
        takes the root dependency and resolves all its unresolved
        dependencies, but only one level down.
        """
        # Copy it as we have to change it as we walk along the list
        resolved_deps: List[StructuralDependency] = []

        for unres in root.dependencies:
            resolved_dep = self._resolve_single_dep(root, unres, 0, False)
            resolved_deps.append(resolved_dep)

        # At this point, we have a full first level resolution done.
        root.dependencies = resolved_deps

    def _resolve_single_dep(self,
                            parent: Union[RootDependency, ResolvedDependency],
                            dep: StructuralDependency,
                            level: int,
                            report_resolve: bool
                            ) -> ResolvedDependency:

        if isinstance(dep, ResolvedDependency):
            # pass already resolved ones.
            return dep

        resolved_dep = self.resolved_cache.get(dep.name)
        if resolved_dep is not None:
            logger.info(f"Dependency {dep.name} already found.")
            # We already found the dependency, but we need to add the
            # category if it's not already there, and to all the subtree
            # as well
            if not self._check_constraints(parent, resolved_dep, dep):
                msg = (
                    f"Unable to satisfy subdependency {dep.name} constraint"
                )
                if not isinstance(parent, RootDependency):
                    msg += f" for dependency {parent.name}."
                raise CannotResolveError(msg)

            resolved_dep.add_categories_recursive(dep.categories)
            if report_resolve:
                self._report_resolve(resolved_dep, level, True)
            return resolved_dep

        # Could not find, do the lookup
        if is_core_dependency(dep.name):
            logger.info(f"Dependency {dep.name} is a core dependency")
            resolved_dep = ResolvedCoreDependency(
                name=dep.name,
                categories=dep.categories,
                dependencies=[]
            )
        elif isinstance(dep, UnresolvedConstrainedDependency):
            resolved_dep = self._resolve_by_constraint(dep)
        elif isinstance(dep, UnresolvedVCSDependency):
            resolved_dep = self._resolve_by_vcs(dep)
        elif isinstance(dep, UnresolvedDependency):
            raise CannotResolveError(
                f"Undefined type of unresolved dependency {dep}")

        self.resolved_cache[dep.name] = resolved_dep
        if report_resolve:
            self._report_resolve(resolved_dep, level, False)
        return resolved_dep

    def _resolve_by_constraint(self,
                               unresolved: UnresolvedConstrainedDependency
                               ) -> ResolvedSourceDependency:
        """Resolve a dependency by its constraint from the source
        groups. THe resulting resolved dependency will have its own
        dependencies unresolved.
        """

        # Find the package that satisfies the constraints
        try:
            package = self.source_group.find_most_recent_package(
                unresolved.name, unresolved.constraint)
        except PackageNotFoundError:
            raise CannotResolveError(f"Unable to find package for "
                                     f"dependency {unresolved.name}")

        logger.info(f"Found package {package.name} {package.version} "
                    f"to resolve {unresolved.name} {unresolved.constraint}")
        logger.info(f"Package {package.name} has sub-dependencies:")

        # Ensure it to be downloaded
        package.ensure_local()

        # Check its dependencies and add them as unresolved.
        subdep_list = _extract_subdeps(package)
        for subdep in subdep_list:
            subdep.categories = unresolved.categories

        resolved_dep = ResolvedSourceDependency(
            name=package.name,
            package=package,
            categories=unresolved.categories,
            r_constraint=_constraint_list_to_object(package.r_constraint),
            dependencies=subdep_list
        )

        return resolved_dep

    def _resolve_by_vcs(self,
                        unresolved: UnresolvedVCSDependency
                        ) -> ResolvedVCSDependency:
        """Resolve a VCS unresolved dependency"""
        logger.info(f"Cloning {unresolved.name} from {unresolved.url}")

        vcs_store = VCSStore()
        try:
            vcs_clone_shallow(
                unresolved.vcs_type,
                unresolved.url,
                unresolved.ref,
                vcs_store.clone_dir(unresolved.url, unresolved.ref))
        except ValueError as e:
            raise CannotResolveError(f"VCS clone failed: {e}") from None

        package = DirPackage(
            vcs_store.clone_dir(unresolved.url, unresolved.ref))
        subdep_list = _extract_subdeps(package)
        for subdep in subdep_list:
            subdep.categories = unresolved.categories

        resolved_dep = ResolvedVCSDependency(
            name=unresolved.name,
            vcs_type="git",
            url=unresolved.url,
            ref=unresolved.ref,
            categories=unresolved.categories,
            dependencies=subdep_list
        )

        vcs_store.clear()
        return resolved_dep

    def _resolve_tree_depth_first(self, root: RootDependency) -> None:
        """Resolve the tree depth first"""
        for d in root.dependencies:
            d = cast(ResolvedDependency, d)
            self._report_resolve(d, 0, False)
            self._depth_first_resolve(d, 1)

    def _depth_first_resolve(self,
                             dependency: ResolvedDependency,
                             level: int) -> None:
        """
        Resolves the tree emanated by the given dependency.
        This function updates the dependency object. The resulting
        new dependencies list will have resolved dependencies whose
        subtrees are also fully resolved.
        """
        # Copy it as we have to change it as we walk along the list
        resolved_deps: List[StructuralDependency] = []

        logger.info(f"Doing depth first resolve on {dependency.name}")

        for subdep in dependency.dependencies:
            resolved_dep = self._resolve_single_dep(
                dependency, subdep, level, True
            )
            # Recurse
            self._depth_first_resolve(resolved_dep, level + 1)

            resolved_deps.append(resolved_dep)

        dependency.dependencies = resolved_deps

    def _check_constraints(self,
                           parent: Union[RootDependency, ResolvedDependency],
                           resolved: ResolvedDependency,
                           unresolved: UnresolvedDependency) -> bool:
        """
        Checks if the resolved dependency we have in the cache
        satisfies the unresolved dependency constraint.
        """

        # The problem here is that this really depends on the type
        # of dependency we found in the cache, and the type of unresolved
        # dependency we found in the tree.

        if isinstance(unresolved, UnresolvedConstrainedDependency):
            if isinstance(resolved, ResolvedSourceDependency):
                # ResolvedSourceDependency have a package attached
                # so the version is non-ambiguous at the time of locking.
                if not unresolved.constraint.allows(
                        Version.parse(resolved.package.version)):
                    msg = (
                        f"[error]Unable to satisfy subdependency constraint: "
                        f"Already found dependency "
                        f"{resolved.package.name} "
                        f"{resolved.package.version} cannot "
                        f"satisfy constraint {unresolved.name} "
                        f"{unresolved.constraint}")
                    if not isinstance(parent, RootDependency):
                        msg += f" for dependency {parent.name}"
                    msg += "[/error]"
                    console().print(msg)
                    return False
                return True
            elif isinstance(resolved, ResolvedVCSDependency):
                msg = f"[warning]Constrained unresolved dependency " \
                      f"{unresolved.name} "
                if not isinstance(parent, RootDependency):
                    msg += f"for package {parent.name} "
                msg += (
                    f"is resolved with VCS dependency {resolved.url}. "
                    f"At this stage, no assumptions can be made on the "
                    f"actual version that will be downloaded at installation "
                    f"time. [/warning]"
                )
                console().print(msg)
                return True
            elif isinstance(resolved, ResolvedCoreDependency):
                return True
            else:
                raise TypeError(f"Unable to check constraints for unknown "
                                f"type {resolved}")
        elif isinstance(unresolved, UnresolvedVCSDependency):
            if not isinstance(resolved, ResolvedVCSDependency):
                console().print(
                    f"[warning]VCS dependency {unresolved.name} has been "
                    f"resolved by previously found non-VCS dependency. "
                    f"The resolution will continue regardless.[/warning]"
                )
            return True

        raise TypeError(f"Unable to check constraints for unknown "
                        f"type {unresolved}")

    def _report_resolve(self,
                        resolved_dep: ResolvedDependency,
                        level: int,
                        already_found: bool):
        """Prints out that a dependency has been resolved to the user"""
        if isinstance(resolved_dep, ResolvedSourceDependency):
            version = (
                resolved_dep.package.version
                if not already_found else "..."
            )
            console().print(
                " "*(2 + 2*level)
                + f"- [package]{resolved_dep.package.name}[/package] "
                + f"([version]{version}[/version])"
            )
        elif isinstance(resolved_dep, ResolvedVCSDependency):
            ref = resolved_dep.ref
            if ref is None:
                ref = "HEAD"

            console().print(
                " "*(2 + 2*level)
                + f"- [package]{resolved_dep.name}[/package] "
                + f"([version]{resolved_dep.vcs_type}@{ref}[/version])"
            )


def _constraint_list_to_object(constraint_list: list) -> VersionConstraint:
    """Converts the list of constraint into a VersionConstraint object"""

    constraint_string = ",".join(constraint_list)

    if len(constraint_string) == 0:
        constraint_string = "*"

    return parse_constraint(constraint_string)


def is_core_dependency(dependency_name: str) -> bool:
    return dependency_name in (
        "R", "stats", "utils", "graphics", "grDevices",
        "methods", "tools", "parallel", "splines", "grid",
        "compiler", "datasets", "stats4", "tcltk", "translations"
    )


def _extract_subdeps(package: PackageABC) -> List[StructuralDependency]:
    # Extract the dependencies of the found package
    subdep_list: List[StructuralDependency] = []
    for subdep in package.dependencies:
        logger.info(f" - {subdep.name}")
        unresolved_subdep = UnresolvedConstrainedDependency(
            name=subdep.name,
            constraint=_constraint_list_to_object(subdep.constraint),
            categories=[]
        )
        subdep_list.append(unresolved_subdep)

    return subdep_list
