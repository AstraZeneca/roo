import logging
import pathlib
from typing import Union, List, cast, Generator

from .caches.build_cache import BuildCache
from .caches.vcs_store import VCSStore
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
from .user_notifier import NullNotifier, NotifierABC

logger = logging.getLogger(__file__)


class InstallationError(Exception):
    pass


class Installer:
    """
    Class able to perform installation of packages in environments.
    """

    def __init__(self,
                 notifier: Union[NotifierABC, None] = None,
                 verbose_build: bool = False,
                 serial: bool = False):
        """
        Initialise the installer.

        Args:
            notifier: An instance of the notifier.
                      If None, a NullNotifier will be used.
            verbose_build: Defines if the build should be verbose or not
            serial: Defines if the installation and build should be in serial,
                    or parallelised across multiple processes.
        """
        if notifier is None:
            notifier = NullNotifier()

        self._notifier = notifier
        self._verbose_build = verbose_build
        self._serial = serial

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

        self._notifier.message(
            f"Installing {', '.join(install_dep_categories)} "
            f"dependencies from lockfile.")

        deptree = lock_entries_to_deptree(source_group, lockfile.entries)
        # First do all the downloading required
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

        # Then restart and do all the installing
        plan = plan_generator(deptree, install_dep_categories)
        for dep in plan:
            if isinstance(dep, ResolvedVCSDependency):
                self._install_package_from_vcs(dep, environment)
            elif isinstance(dep, ResolvedSourceDependency):
                self._install_package_from_source(dep, environment)
            elif isinstance(dep, (RootDependency, ResolvedCoreDependency)):
                pass
            else:
                raise InstallationError(f"Unknown dependency {dep}")

    def _checkout_from_vcs(self, dep: ResolvedVCSDependency):
        logger.info(f"Cloning {dep.name} from VCS {dep.url}")

        cache = VCSStore(dep.url)
        self._notifier.message(
            f"- Cloning [package]{dep.name}[/package] "
            f"from {dep.url}",
            indent=2
        )

        cache.clear_clone(dep.ref)
        vcs_clone_shallow(dep.vcs_type, dep.url, dep.ref,
                          cache.clone_dir(dep.ref))

    def _ensure_local_source_package(self, dep: ResolvedSourceDependency):
        """Ensures that the packages have been downloaded
        and have the correct hash."""
        source_package = dep.package

        if dep.package.has_local_file() and dep.package.hash_match():
            return

        self._notifier.message(
            f"- Downloading [package]{source_package.name}[/package] "
            f"([version]{source_package.version}[/version])",
            indent=2)

        # Either we don't have the package or the file is there but it
        # was cut short during download so it's broken. Act as if it's
        # not there.
        source_package.download()

        if not source_package.hash_match():
            raise InstallationError(
                f"Hash for package "
                f"{source_package.name} {source_package.version}, "
                f"file {source_package.filename} is different from the "
                f"expected.")

    def _install_package_from_vcs(self,
                                  dep: ResolvedVCSDependency,
                                  environment: Environment):
        """Install a VCS package"""
        # VCS packages must be checked out to a temp directory
        # every time, otherwise we'll get conflicts between parallel
        # executions that may be cloning and switching at the same
        # time.

        installed_version = environment.package_version(dep.name)
        executor = environment.executor()
        executor.quiet = not self._verbose_build

        logger.info(
            f"Installing {dep.name} from VCS {dep.url}"
            f"in environment {environment.name}"
        )

        vcs_store = VCSStore(dep.url)
        logger.info(f"Using vcs store at {vcs_store.base_dir}")

        try:
            vcs_clone_shallow(
                dep.vcs_type, dep.url, dep.ref, vcs_store.clone_dir(dep.ref)
            )
        except ValueError as e:
            raise InstallationError(f"VCS clone failed: {e}") from None

        op_str = ("Installing"
                  if installed_version is None else "Replacing")

        self._notifier.message(
            f"- {op_str} [package]{dep.name}[/package] ", indent=2)

        if installed_version is not None:
            executor.remove(dep.name)

        try:
            executor.install(vcs_store.clone_dir(dep.ref))
        except ExecutorError as e:
            raise InstallationError(f"Unable to install {dep.name}: {e}")

        # Delete the cache only in case of success, so it's easier to check
        # what went wrong in case of error.
        vcs_store.clear_clone(dep.ref)

        logger.info(
            f"Package {dep.name} successfully "
            f"installed in environment {environment.name}"
        )

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
        executor = environment.executor()
        executor.quiet = not self._verbose_build
        version_info = environment.r_version_info
        cache = BuildCache(version_info["version"], version_info["platform"])

        logger.info(
            f"Installing {package.name} {package.version} "
            f"in environment {environment.name}"
        )

        op_str = "Installing"
        version_str = package.version
        cached_str = ""
        if installed_version is not None:
            op_str = "Replacing"
            version_str = f"{installed_version} -> {package.version}"
        if cache.has_build(package.name, package.version):
            cached_str = "(cached)"

        msg = (f"- {op_str} [package]{package.name}[/package] "
               f"([version]{version_str}[/version]) {cached_str}")
        self._notifier.message(msg, indent=2)

        if installed_version is not None:
            executor.remove(package.name)

        if cache.has_build(package.name, package.version):
            cache.restore_build(
                package.name,
                package.version,
                environment.lib_dir / dep.name)
        else:
            try:
                executor.install(cast(pathlib.Path, package.local_path))
            except ExecutorError as e:
                raise InstallationError(f"Unable to install {dep.name}: {e}")
            cache.add_build(
                package.name, package.version,
                environment.lib_dir / dep.name
            )

        logger.info(
            f"Package {dep.name} successfully "
            f"installed in environment {environment.name}"
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
