import logging
import pathlib
from typing import List, cast, Generator

from roo.caches.vcs_store import VCSStore
from roo.semver import Version

from .caches.build_cache import BuildCache
from .deptree.dependencies import ResolvedDependency, RootDependency, \
    ResolvedSourceDependency, ResolvedVCSDependency, ResolvedCoreDependency
from .deptree.transforms import lock_entries_to_deptree
from .deptree.traverse import traverse_breadth_first_layered
from .environment import Environment
from .parsers.lock import Lock
from .parsers.rproject import RProject
from .r_executor import ExecutorError
from .sources.source_group import create_source_group_from_config_list
from .sources.vcs import vcs_clone_shallow
from .console import console

logger = logging.getLogger(__file__)


class InstallationError(Exception):
    pass


class Installer:
    """
    Class able to perform installation of packages in environments.
    """

    def __init__(self,
                 verbose_build: bool = False,
                 serial: bool = False,
                 use_vanilla: bool = False):
        """
        Initialise the installer.

        Args:
            verbose_build: Defines if the build should be verbose or not
            serial: Defines if the installation and build should be in serial,
                    or parallelised across multiple processes.
            use_vanilla: specify --use-vanilla for CMD INSTALL
        """
        self._verbose_build = verbose_build
        self._serial = serial
        self._use_vanilla = use_vanilla

        # This is a temp dir where we put all our clones from VCS.
        # It is guaranteed that the store is different for each invocation,
        # so we never risk an issue of one process stomping on another
        # process cloning.
        self._vcs_store = VCSStore()

    def install_lockfile(self,
                         lockfile: Lock,
                         environment: Environment,
                         install_dep_categories: list = None,
                         ) -> None:
        """
        Installs the content of a given lockfile into an environment.

        Args:
            lockfile: the lockfile to install
            environment: The target environment
            install_dep_categories: list of the categories to install.
            If None, install all categories.

        Returns: None

        """
        if install_dep_categories is None:
            install_dep_categories = RProject.ALL_DEPENDENCY_CATEGORIES

        source_group = create_source_group_from_config_list(
            lockfile.sources)

        # Make sure we start from a clear cache for VCS.
        # This may happen if we perform an install lockfile twice and the
        # first one fails, leaving stuff in the cache.

        logger.info("Clearing cache for VCS")
        self._vcs_store.clear()

        console().print(
            f"Installing {', '.join(install_dep_categories)} "
            f"dependencies from lockfile in environment "
            f"[environment]{environment.name}[/environment].")

        deptree = lock_entries_to_deptree(source_group, lockfile.entries)
        # I am forced to go through the plan three times.
        # First is to check that all R constraints are satisfied with the
        # current version of R we are using, so we don't waste time building
        # a doomed attempt
        executor = environment.executor(
            quiet=not self._verbose_build,
            use_vanilla=self._use_vanilla
        )
        r_version = executor.version
        plan = plan_generator(deptree, install_dep_categories)
        for dep in plan:
            if isinstance(dep, ResolvedSourceDependency):
                if not (dep.r_constraint.allows(Version.parse(r_version))):
                    console().print(
                        f"[error]Cannot install {dep.name} in environment "
                        f"{environment.name}. "
                        f"{dep.name} requires R {dep.r_constraint} but "
                        f"environment is for R {r_version}[/error]"
                    )
                    raise InstallationError(
                        f"R version violation for {dep.name}"
                    )

        # Then do all the downloading required so that we get this over with
        # and we can install freely
        plan = plan_generator(deptree, install_dep_categories)
        for dep in plan:
            if isinstance(dep, ResolvedVCSDependency):
                self._checkout_from_vcs(dep)
            elif isinstance(dep, ResolvedSourceDependency):
                self._ensure_local_source_package(dep)
            elif isinstance(dep, (RootDependency, ResolvedCoreDependency)):
                pass
            else:
                raise InstallationError(f"Unknown dependency {dep}")

        # Then restart and do all the installing.
        plan = plan_generator(deptree, install_dep_categories)
        for dep in plan:
            if isinstance(dep, ResolvedVCSDependency):
                self._install_package_from_vcs_store(dep, environment)
            elif isinstance(dep, ResolvedSourceDependency):
                self._install_package_from_source(dep, environment)
            elif isinstance(dep, (RootDependency, ResolvedCoreDependency)):
                pass
            else:
                raise InstallationError(f"Unknown dependency {dep}")

        # it's all gone well, so let's delete the cache
        logger.info("Clearing cache for VCS")
        self._vcs_store.clear()

    def _checkout_from_vcs(self, dep: ResolvedVCSDependency):
        logger.info(f"Cloning {dep.name} from VCS {dep.url}@{dep.ref}")

        vcs_store = self._vcs_store
        with console().status(
                f"Cloning [package]{dep.name}[/package] "
                f"from {dep.url}@{dep.ref}"):
            vcs_store.clear_clone(dep.url, dep.ref)
            vcs_clone_shallow(dep.vcs_type, dep.url, dep.ref,
                              vcs_store.clone_dir(dep.url, dep.ref))

    def _ensure_local_source_package(self, dep: ResolvedSourceDependency):
        """Ensures that the packages have been downloaded
        and have the correct hash."""
        source_package = dep.package

        if dep.package.has_local_file() and dep.package.hash_match():
            return

        with console().status(
                f"[message]Downloading[/message] "
                f"[package]{source_package.name}[/package] "
                f"([version]{source_package.version}[/version]) "
                f"from {source_package.source.name}"):
            # Either we don't have the package or the file is there but it
            # was cut short during download so it's broken. Act as if it's
            # not there.
            source_package.retrieve()

        console().print(
            f":white_check_mark: [success]Downloaded[/success] "
            f"[package]{source_package.name}[/package] "
            f"([version]{source_package.version}[/version]) "
            f"from {source_package.source.name}"
        )

        if not source_package.hash_match():
            raise InstallationError(
                f"Hash for package "
                f"{source_package.name} {source_package.version}, "
                f"file {source_package.filename} is different from the "
                f"expected.")

    def _install_package_from_vcs_store(self,
                                        dep: ResolvedVCSDependency,
                                        environment: Environment):
        """Install a VCS package"""
        # At this stage, we assume that the package has been checked
        # out in the temporary directory, and we don't have to perform
        # the cloning again.

        installed_version = environment.package_version(dep.name)
        executor = environment.executor(
            quiet=not self._verbose_build,
            use_vanilla=self._use_vanilla
        )

        logger.info(
            f"Installing {dep.name} from VCS {dep.url}"
            f"in environment {environment.name}"
        )

        vcs_store = self._vcs_store
        logger.info(f"Using vcs store at {vcs_store.root_dir}")

        with console().status(
                f"[message]Building[/message] "
                f"[package]{dep.name}[/package] "
                f"from VCS {dep.url}@{dep.ref}"
        ) as status:
            if installed_version is not None:
                status.update(
                    status=f"[message]Removing currently installed[/message] "
                           f"[package]{dep.name}[/package] "
                           f"[version]{installed_version}[/version]"
                )
                executor.remove(dep.name)

            status.update(
                status=f"[message]Building[/message] "
                       f"[package]{dep.name}[/package] "
                       f"from VCS {dep.url}@{dep.ref}")
            try:
                executor.install(vcs_store.clone_dir(dep.url, dep.ref))
            except ExecutorError as e:
                raise InstallationError(f"Unable to install {dep.name}: {e}")

        logger.info(
            f"Package {dep.name} successfully "
            f"installed in environment {environment.name}"
        )

        console().print(
            f":white_check_mark: [success]Installed[/success] "
            f"[package]{dep.name}[/package] from VCS {dep.url}@{dep.ref}")

        # Delete the cache only in case of success, so it's easier to check
        # what went wrong in case of error.
        vcs_store.clear_clone(dep.url, dep.ref)

    def _install_package_from_source(self,
                                     dep: ResolvedSourceDependency,
                                     environment: Environment):
        package = dep.package
        # already installed
        if environment.has_package(package.name, package.version):
            logger.info(
                f"Package {package.name} {package.version} "
                f"already present in environment. Skipping.")
            return

        installed_version = environment.package_version(package.name)
        executor = environment.executor(
            quiet=not self._verbose_build,
            use_vanilla=self._use_vanilla
        )
        version_info = environment.r_version_info
        cache = BuildCache(version_info["version"], version_info["platform"])

        logger.info(
            f"Installing {package.name} {package.version} "
            f"in environment {environment.name}"
        )

        op_str = "Installing"
        version_str = f"[version]{package.version}[/version]"
        cached_str = ""
        if installed_version is not None:
            op_str = "Replacing"
            version_str = (
                f"[version]{installed_version}[/version] -> "
                f"[version]{package.version}[/version]"
            )
        if cache.has_build(package.name, package.version):
            cached_str = "(from cache)"

        with console().status(
                f"[message]{op_str}[/message] "
                f"[package]{package.name}[/package] "
                f"([version]{version_str}[/version]) {cached_str}"
        ) as status:

            if installed_version is not None:
                status.update(
                    f"[message]Removing previous version[/message]"
                    f"[package]{package.name}[/package] "
                    f"([version]{installed_version}[/version])")
                executor.remove(package.name)

            if cache.has_build(package.name, package.version):
                status.update(
                    f"[message]Reinstalling[/message] "
                    f"[version]{package.name}[/version] "
                    f"([version]{package.version}[/version]) "
                    f"(from cache)")
                cache.restore_build(
                    package.name,
                    package.version,
                    environment.lib_dir / dep.name)
            else:
                status.update(
                    f"[message]Building[/message] "
                    f"[version]{package.name}[/version] "
                    f"([version]{package.version}[/version])")
                try:
                    executor.install(cast(pathlib.Path, package.local_path))
                except ExecutorError as e:
                    raise InstallationError(
                        f"Unable to install {dep.name}: {e}")
                cache.add_build(
                    package.name, package.version,
                    environment.lib_dir / dep.name
                )
        logger.info(
            f"Package {dep.name} successfully "
            f"installed in environment {environment.name}"
        )
        console().print(
            f":white_check_mark: [success]Installed[/success] "
            f"[package]{package.name}[/package] "
            f"({version_str}) {cached_str}"
        )


def plan_generator(deptree: RootDependency,
                   install_dep_categories: List[str]
                   ) -> Generator[ResolvedDependency, None, None]:
    """
    The install plan is a list of lists of dependencies to install.
    Each list is a layer. layers are ordered so that the packages at the
    bottom of the dependency tree are yielded first.
    """
    layers = reversed(traverse_breadth_first_layered(deptree))

    for layer in layers:
        for dep in layer:
            if not isinstance(dep, RootDependency) and \
                    set(dep.categories).intersection(
                        set(install_dep_categories)):
                if not isinstance(dep, ResolvedDependency):
                    raise TypeError(
                        f"Cannot return a plan containing an "
                        f"unresolved dependency {dep}")
                yield dep
