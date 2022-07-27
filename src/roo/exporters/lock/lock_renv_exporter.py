from typing import Dict
import pathlib
import logging
import atomicwrites
import json

from ..exceptions import ExportError
from .base_exporter import BaseExporter
from ...parsers.lock import Lock, source_by_name, SourceLockEntry

logger = logging.getLogger(__name__)


class LockRenvExporter(BaseExporter):
    def export(self, lock: Lock, path: pathlib.Path):
        if lock.has_vcs_packages():
            raise ExportError("Unable to export locks with VCS packages")

        content: Dict[str, dict] = {
            "R": {
            }
        }

        repositories = []
        for source in lock.sources:
            repositories.append({
                "Name": source.name,
                "URL": source.url
            })

        content["R"]["Repositories"] = repositories

        packages = {}

        source_entries = [
            entry for entry in lock.entries
            if isinstance(entry, SourceLockEntry)
        ]

        for entry in sorted(source_entries, key=lambda x: x.name):
            source = source_by_name(lock.sources, entry.source)
            # If md5s are not found, we cannot continue

            if entry.files[0].md5 is None:
                raise ExportError(
                    "The current roo lock file contains no md5 hashes"
                )

            packages[entry.name] = {
                "Package": entry.name,
                "Version": entry.version,
                "Source": "Repository",
                "Repository": source.name,
                # Take the first file. I can't be bothered to decide otherwise
                # at the moment.
                "Hash": entry.files[0].md5
            }
        content["Packages"] = packages

        try:
            with atomicwrites.atomic_write(
                    path, overwrite=True, newline="", encoding="utf-8") as f:
                json.dump(content, f, indent=4)
        except Exception as e:
            logger.exception(f"Unable to export to renv: {e}")
            raise ExportError(f"{e}")
