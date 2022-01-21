from typing import List, Dict, cast

from roo.semver import parse_constraint

from ..parsers.lock import LockEntry, RootLockEntry, SourceLockEntry, \
    VCSLockEntry, CoreLockEntry, PackageFile
from .dependencies import RootDependency, ResolvedDependency, \
    ResolvedSourceDependency, ResolvedVCSDependency, ResolvedCoreDependency, \
    UnresolvedDependency, UnresolvedConstrainedDependency, \
    UnresolvedVCSDependency, StructuralDependency
from ..parsers.rproject import Dependency as RProjectDependency
from ..sources.source_group import SourceGroup
from .traverse import traverse_depth_first_unique


def lock_entries_to_deptree(
        source_group: SourceGroup,
        entries: List[LockEntry]) -> RootDependency:
    """Convert the entries from the lock file back into the
    fully resolved dependency tree."""

    root = RootDependency(dependencies=[])

    if len(entries) == 0:
        return root

    # Reconstruct the flattened tree, but leave the dependencies of each entry
    # unresolved for now. We'll bind them afterwards. To do so, keep track of
    # them with this index
    all_deps: Dict[str, ResolvedDependency] = {}

    for entry in entries:
        if isinstance(entry, RootLockEntry):
            root.dependencies = [
                UnresolvedDependency(name=d, categories=[])
                for d in entry.dependencies
            ]
        elif isinstance(entry, SourceLockEntry):
            source = source_group.source_by_name(entry.source)
            source_package = source.find_package(entry.name, entry.version)
            source_package.expected_hash = entry.files[0].hash
            all_deps[entry.name] = ResolvedSourceDependency(
                name=entry.name,
                categories=entry.categories,
                package=source_package,
                r_constraint=parse_constraint(entry.r_constraint),
                dependencies=[
                    UnresolvedDependency(
                        name=d,
                        categories=entry.categories,
                    )
                    for d in entry.dependencies
                ]
            )
        elif isinstance(entry, VCSLockEntry):
            all_deps[entry.name] = ResolvedVCSDependency(
                name=entry.name,
                vcs_type=entry.vcs_type,
                url=entry.url,
                ref=entry.ref,
                categories=entry.categories,
                dependencies=[
                    UnresolvedDependency(
                        name=d,
                        categories=entry.categories,
                    )
                    for d in entry.dependencies
                ]
            )
        elif isinstance(entry, CoreLockEntry):
            all_deps[entry.name] = ResolvedCoreDependency(
                name=entry.name,
                categories=entry.categories,
                dependencies=[]
            )
        else:
            raise TypeError(f"Unrecognised entry {entry}")

    # now, resolve all the dependencies
    for dep in all_deps.values():
        dep.dependencies = [
            all_deps[unresolved.name] for unresolved in dep.dependencies
        ]

    # Then, resolve the root ones.
    root.dependencies = [
        all_deps[unresolved.name] for unresolved in root.dependencies
    ]

    # and finally, return the root
    return root


def deptree_to_lock_entries(root: RootDependency) -> List[LockEntry]:
    """
    Converts the dependency tree into the linearized list of entries
    for addition to the lock file.
    """
    # It is required that the whole tree is resolved fully.
    # We assume so because we run this algorithm on the fully resolved tree,
    # hence we cast all subdependencies to a resolved dependency.

    lock_entries: List[LockEntry] = []
    for dependency in traverse_depth_first_unique(root):
        if isinstance(dependency, ResolvedCoreDependency):
            lock_entries.append(
                CoreLockEntry(
                    name=dependency.name,
                    categories=dependency.categories,
                    dependencies=[]
                )
            )
            continue

        dependencies = [
            cast(ResolvedDependency, x).name
            for x in cast(ResolvedDependency, dependency).dependencies]

        if isinstance(dependency, RootDependency):
            lock_entries.append(
                RootLockEntry(
                    categories=[],
                    dependencies=dependencies
                )
            )
        elif isinstance(dependency, ResolvedSourceDependency):
            lock_entries.append(
                SourceLockEntry(
                    name=dependency.package.name,
                    version=dependency.package.version,
                    source=dependency.package.source.name,
                    categories=dependency.categories,
                    r_constraint=str(dependency.r_constraint),
                    files=[
                        PackageFile(
                            name=dependency.package.filename,
                            hash=dependency.package.hash
                        )
                    ],
                    dependencies=dependencies
                ))
        elif isinstance(dependency, ResolvedVCSDependency):
            lock_entries.append(
                VCSLockEntry(
                    name=dependency.name,
                    vcs_type=dependency.vcs_type,
                    url=dependency.url,
                    ref=dependency.ref,
                    dependencies=dependencies,
                    categories=dependency.categories
                )
            )
        else:
            raise TypeError(
                f"No clue what to write in the package for {dependency}")

    return lock_entries


def rproject_to_deptree(rproject_deps: List[RProjectDependency]
                        ) -> RootDependency:
    """Creates the initial tree of unresolved dependencies to feed into
    the resolver from the rproject file the user provided"""
    dependencies: List[StructuralDependency] = []

    for rp_dep in rproject_deps:
        if rp_dep.constraint is not None:
            dependencies.append(
                UnresolvedConstrainedDependency(
                    name=rp_dep.name,
                    constraint=rp_dep.constraint,
                    categories=[rp_dep.category],
                )
            )
        elif rp_dep.vcs_spec is not None:
            dependencies.append(
                UnresolvedVCSDependency(
                    name=rp_dep.name,
                    categories=[rp_dep.category],
                    vcs_type="git",
                    url=rp_dep.vcs_spec.git,
                    ref=rp_dep.vcs_spec.branch
                )
            )
        else:
            raise ValueError(
                f"Unknown rproject specification for dependency {rp_dep.name}"
            )

    return RootDependency(dependencies=dependencies)
