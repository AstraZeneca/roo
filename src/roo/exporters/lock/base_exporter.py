import pathlib

from ...parsers.lock import Lock


class BaseExporter:
    def export(self, lock: Lock, path: pathlib.Path):
        pass
