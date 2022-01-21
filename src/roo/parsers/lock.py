from __future__ import annotations
import dataclasses
from io import TextIOWrapper
from typing import Optional, Union, List, Dict, MutableMapping, Any

import atomicwrites
import toml
import pathlib

from ..parsers.exceptions import ParsingError


@dataclasses.dataclass
class Metadata:
    """Metainformation contained in the lock file"""
    # The version of the lock file
    version: int = 2
    # a hash to see if the lock is synced with the current rproject file
    content_hash: Optional[str] = None
    # Flag to state if the packages were determined in conservative mode
    # (minimal difference)
    conservative: bool = False
    # The environment id, if it was specified in the rproject
    env_id: Optional[str] = None

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> Metadata:
        return cls(
            version=d.get("version", 0),
            content_hash=d.get("content_hash"),
            conservative=d["conservative"],
            env_id=d.get("env-id")
        )


@dataclasses.dataclass
class Source:
    """Represents a repository source such as cran or cran-like"""
    name: str
    url: str
    proxy: Optional[Union[str, bool]] = None

    @classmethod
    def fromdict(cls, d: Dict[str, str]) -> Source:
        return cls(
            name=d["name"],
            url=d["url"],
            proxy=d.get("proxy")
        )


@dataclasses.dataclass
class PackageFile:
    """Describes a specific package file"""
    name: str
    hash: str

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> PackageFile:
        return cls(**d)


@dataclasses.dataclass
class LockEntry:
    """Base class for the entries in the lock file"""
    # To which categories it belongs to
    categories: List[str]
    # The dependencies of this package, as a list of dependency strings
    dependencies: List[str]

    def asdict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["categories"] = sorted(d["categories"])
        d["dependencies"] = sorted(d["dependencies"])
        return d


@dataclasses.dataclass
class RootLockEntry(LockEntry):
    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> RootLockEntry:
        return cls(**d)

    def asdict(self) -> Dict[str, Any]:
        d = super().asdict()
        d["type"] = "root"
        return d


@dataclasses.dataclass
class SourceLockEntry(LockEntry):
    # The name of the package. Empty if it's the root package
    name: str
    # The version of the package. Empty if it's the root package or a VCS pkg
    version: str
    # If string, it refers to one of the sources names.
    source: str
    # The files description
    files: List[PackageFile]
    # The constraint on the R version
    r_constraint: str

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> SourceLockEntry:
        if "r_constraint" not in d:
            d["r_constraint"] = "*"

        self = cls(**d)
        self.files = [PackageFile.fromdict(x) for x in d["files"]]
        return self

    def asdict(self) -> Dict[str, Any]:
        d = super().asdict()
        d["type"] = "source"
        return d


@dataclasses.dataclass
class VCSLockEntry(LockEntry):
    # The name of the package.
    name: str
    # the type of VCS, for now only git.
    vcs_type: str
    # the URL of the VCS
    url: str
    # the reference to checkout.
    ref: Optional[str]

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> VCSLockEntry:
        if "ref" not in d:
            d["ref"] = None
        return cls(**d)

    def asdict(self) -> Dict[str, Any]:
        d = super().asdict()
        d["type"] = "vcs"
        return d


@dataclasses.dataclass
class CoreLockEntry(LockEntry):
    # The name of the package.
    name: str

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> CoreLockEntry:
        return cls(**d)

    def asdict(self) -> Dict:
        d = super().asdict()
        d["type"] = "core"
        return d


class Lock:
    """Represents a Lock. This is normally saved as a file called roo.lock
    and represents a fixed set of versions of the various packages to install,
    as well as their dependencies so that they are installed in the proper
    order"""

    def __init__(self):
        # The list of sources configured in the file
        self.sources: List[Source] = []

        # the list of entries this lock contains
        self.entries: List[LockEntry] = []

        # Metainformation that is stored in the file
        self.metadata: Metadata = Metadata()

        # represent the source path where this info came from.
        self.path: Optional[pathlib.Path] = None

    def has_vcs_packages(self) -> bool:
        """Returns True if any of the packages is from a VCS source"""
        for entry in self.entries:
            if isinstance(entry, VCSLockEntry):
                return True
        return False

    @classmethod
    def parse(cls,
              fileobj_or_path: Union[TextIOWrapper, pathlib.Path]
              ) -> Lock:
        """Parses a file object or path."""
        try:
            tomldata = toml.load(fileobj_or_path)
        except toml.TomlDecodeError:
            raise ParsingError(
                "Toml file may be corrupted or in the wrong format"
            )

        if isinstance(fileobj_or_path, TextIOWrapper):
            original_path = pathlib.Path(fileobj_or_path.name)
        else:
            original_path = fileobj_or_path

        self = cls()

        metadata = tomldata.get("metadata", {})
        version = metadata.get("version", 0)
        if not cls._can_parse_version(version):
            raise ParsingError(
                f"The current lock file version {version} "
                "cannot be parsed by this version of roo."
            )

        self.path = original_path
        self.metadata = Metadata.fromdict(metadata)

        self.sources = [
            Source.fromdict(entry)
            for entry in tomldata["source"]
        ]

        self.entries = self._parse_entries(tomldata)
        return self

    def save(self, path: Optional[pathlib.Path] = None):
        """Save the lock file to a given path, if specified
        If not specified, it saves it to the stored path variable.
        If that is None, save it to a default filename.
        """
        tomldata: dict = dict()
        tomldata["source"] = [
            dataclasses.asdict(x) for x in self.sources
        ]

        def sortkey(x):
            try:
                return x.name
            except AttributeError:
                return ""

        tomldata["entry"] = []
        for entry in sorted(self.entries, key=sortkey):
            d = entry.asdict()
            tomldata["entry"].append(d)

        tomldata["metadata"] = dataclasses.asdict(self.metadata)

        if path is None:
            path = self.path

        if path is None:
            path = pathlib.Path("roo.lock")

        with atomicwrites.atomic_write(
                path, encoding="utf-8", overwrite=True) as f:
            toml.dump(tomldata, f)
            self.path = pathlib.Path(path)

    @classmethod
    def _can_parse_version(cls, version: int) -> bool:
        """Returns True if this parser can parse the version of lock file."""
        return version in (2,)

    def _parse_entries(self,
                       tomldata: MutableMapping[str, Any]
                       ) -> List[LockEntry]:
        """Parse the various entries in reading"""
        entries = []

        for entry_data in tomldata["entry"]:
            type_ = entry_data.pop("type", None)
            entry: LockEntry
            if type_ == "vcs":
                entry = VCSLockEntry.fromdict(entry_data)
            elif type_ == "root":
                entry = RootLockEntry.fromdict(entry_data)
            elif type_ == "source":
                entry = SourceLockEntry.fromdict(entry_data)
            elif type_ == "core":
                entry = CoreLockEntry.fromdict(entry_data)
            else:
                raise ParsingError(f"Unknown entry type {type_} in lock file")
            entries.append(entry)

        return entries
