import pathlib
import logging
import atomicwrites
import csv

from ..exceptions import ExportError
from .base_exporter import BaseExporter
from ...parsers.lock import Lock, SourceLockEntry, source_by_name

logger = logging.getLogger(__name__)


class LockCSVExporter(BaseExporter):
    def export(self, lock: Lock, path: pathlib.Path):
        if lock.has_vcs_packages():
            raise ExportError("Unable to export locks with VCS packages")
        try:
            with atomicwrites.atomic_write(
                    path, newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                source_entries = [
                    entry for entry in lock.entries
                    if isinstance(entry, SourceLockEntry)
                ]
                for entry in sorted(source_entries, key=lambda x: x.name):
                    source = source_by_name(lock.sources, entry.source)
                    for pkgfile in entry.files:
                        writer.writerow(
                            [entry.name,
                             entry.version,
                             source.url,
                             pkgfile.name,
                             pkgfile.hash,
                             " ".join(entry.categories)])
        except Exception as e:
            logger.exception(f"Unable to export to csv: {e}")
            raise ExportError(f"{e}")
