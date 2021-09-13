import pathlib
import logging
import atomicwrites

from ..exceptions import ExportError
from .base_exporter import BaseExporter
from ...parsers.lock import Lock, SourceLockEntry

logger = logging.getLogger(__name__)


class LockPackratExporter(BaseExporter):
    # We create a format without the following keys.
    # RVersion: seems to work anyway
    # Hash: the hashes of each package is computed from a complicated
    # algorithm involving the description file. Omitting it does not
    # impact functionality, and if you are using packrat your standards
    # for long term reliability are quite low anyway.
    def export(self, lock: Lock, path: pathlib.Path):
        if lock.has_vcs_packages():
            raise ExportError("Unable to export locks with VCS packages")
        try:
            with atomicwrites.atomic_write(
                    path, newline="", encoding="utf-8") as f:
                source_string = ", ".join([
                    f"{src.name}={src.url}" for src in lock.sources
                ])

                f.writelines([
                    "PackratFormat: 1.4\n",
                    "PackratVersion: 0.5.0\n",
                    f"Repos: {source_string}\n"
                ])

                source_entries = [entry
                                  for entry in lock.entries
                                  if isinstance(entry, SourceLockEntry)]
                for entry in sorted(source_entries, key=lambda x: x.name):
                    f.writelines([
                        "\n"
                        f"Package: {entry.name}\n",
                        f"Source: {entry.source}\n",
                        f"Version: {entry.version}\n",
                    ])
                    if len(entry.dependencies):
                        dependencies_str = ", ".join(entry.dependencies)
                        f.writelines([
                            f"Requires: {dependencies_str}\n"
                        ])
        except Exception as e:
            logger.exception(f"Unable to export to Packrat: {e}")
            raise ExportError(f"{e}")
