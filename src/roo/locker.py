import logging

from roo.console import console

from .parsers.lock import Lock, Source

from .sources.source_group import create_source_group_from_config_list

from .resolver import Resolver
from .parsers.rproject import RProject
from .deptree.transforms import lock_entries_to_deptree, \
    deptree_to_lock_entries, rproject_to_deptree

logger = logging.getLogger(__file__)


class LockerError(Exception):
    pass


class Locker:
    """Class that fills a lock file from the contents of the RProject file"""

    def is_lock_file_sync(self,
                          rproject: RProject,
                          lock_file: Lock,
                          conservative: bool) -> bool:
        """Returns True if the lock file is synchronised with the
        rproject file. Otherwise false"""
        return (
            lock_file.metadata.content_hash == rproject.content_hash and
            lock_file.metadata.conservative == conservative
        )

    def lock(self,
             rproject: RProject, old_lock: Lock, conservative: bool) -> Lock:
        """
        Perform the actual creation of a new lock.

        Args
            rproject:
                the RProject data
            old_lock:
                The old lock file
            conservative:
                if True, only the minimal changes will be performed,
                and the old lock file content will be kept.
                If False, the old lock file content will be thrown away
                and new resolution will take place.

        Returns
            the new lock.
        """
        logger.info("Syncing lock file")

        if self.is_lock_file_sync(rproject, old_lock, conservative):
            console().print(
                "rproject and lock file are already synchronized.")
            return old_lock

        source_group = create_source_group_from_config_list(rproject.sources)
        resolver = Resolver(source_group)

        old_lock_tree = None
        if conservative:
            old_lock_tree = lock_entries_to_deptree(
                source_group,
                old_lock.entries)

        root = rproject_to_deptree(rproject.dependencies)
        resolver.resolve_full_tree(root, old_lock_tree)

        # Create the new lock
        lock = Lock()
        lock.sources = [
            Source(name=r.name, url=r.url, proxy=r.proxy)
            for r in source_group.all_sources
        ]

        lock.entries = deptree_to_lock_entries(root)
        lock.metadata.content_hash = rproject.content_hash
        lock.metadata.env_id = rproject.metadata.env_id
        lock.metadata.conservative = conservative
        return lock
