from __future__ import annotations
import copy
import json
import dataclasses
import pathlib
from hashlib import sha256
from io import TextIOWrapper
from typing import Optional, List, Dict, cast, Union, Any

import atomicwrites
import toml
from toml.decoder import TomlDecodeError

from ..semver import VersionConstraint, parse_constraint
from ..parsers.exceptions import ParsingError


@dataclasses.dataclass
class Metadata:
    name: Optional[str] = None
    version: Optional[str] = None
    authors: Optional[List[str]] = None
    maintainers: Optional[List[str]] = None
    env_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> Metadata:
        self = cls(
            name=d.get("name"),
            version=d.get("version"),
            authors=d.get("authors", cast(List[str], [])),
            maintainers=d.get("maintainers", []),
            env_id=d.get("env-id"),
            title=d.get("title"),
            description=d.get("description"),
            license=d.get("license")
        )
        return self


@dataclasses.dataclass
class Source:
    """Represents a source repository like cran or cran like"""
    name: str
    url: str
    proxy: Optional[Union[str, bool]] = None

    # If True, the source will contain packages that will squash
    # packages from any other source, but only for those packages
    # that exist on this source.
    priority: int = 0

    @classmethod
    def fromdict(cls, d: Dict[str, Any]) -> Source:
        return cls(
            name=d["name"],
            url=d["url"],
            proxy=d.get("proxy"),
            priority=d.get("priority", 0)
        )


@dataclasses.dataclass
class VCSSpec:
    """Represents an entry to define a Version control reference."""
    git: str
    branch: Optional[str]


@dataclasses.dataclass
class Dependency:
    """
    Describes a specified dependency in the rproject file.
    """
    name: str
    constraint: Optional[VersionConstraint]
    category: str
    vcs_spec: Optional[VCSSpec]


class RProject:
    def __init__(self):
        self.path: Optional[pathlib.Path] = None
        self.metadata = Metadata()
        self.dependencies: List[Dependency] = []
        self.sources: List[Source] = []
        self.residual_data: Dict = {}

    # Contains the original file data, purged of the tool.roo section.
    # Used to reconstruct the original file.

    ALL_DEPENDENCY_CATEGORIES = ["main", "dev", "doc"]

    def dependencies_for_category(self, category: str) -> List[Dependency]:
        """Returns a list of dependencies for a given category"""
        return [d for d in self.dependencies if d.category == category]

    @property
    def content_hash(self) -> str:
        """
        Returns a hash that changes if some relevant content has changed.
        This hash is used to determine if the lock file is still synced or not.
        Not all content is relevant to detect change.
        """
        relevant_content = {
            "env-id": self.metadata.env_id
        }

        if len(self.sources):
            relevant_content["source"] = []
            for source in self.sources:
                relevant_content["source"].append(
                    clean_dict({
                        "name": source.name,
                        "url": source.url,
                        "proxy": source.proxy
                    })
                )

        for category in self.ALL_DEPENDENCY_CATEGORIES:
            category_deps = self.dependencies_for_category(category)
            if category_deps is None:
                continue

            if category == "main":
                key = "dependencies"
            else:
                key = f"{category}-dependencies"

            relevant_content[key] = {
                d.name: str(d.constraint) for d in category_deps}

        content_hash = sha256(
            json.dumps(clean_dict(relevant_content), sort_keys=True).encode()
        ).hexdigest()

        return content_hash

    @classmethod
    def parse(cls,
              fileobj_or_path: Union[TextIOWrapper, pathlib.Path]
              ) -> RProject:
        """Parses the data and returns a RProject object"""

        path: Optional[pathlib.Path]

        if isinstance(fileobj_or_path, (str, pathlib.Path)):
            path = fileobj_or_path
            with open(fileobj_or_path, encoding="utf-8") as f:
                data = _read_fileobj(f)
        else:
            data = _read_fileobj(fileobj_or_path)
            path = None

        section = _pop_roo_section(data)

        rproject = cls()
        rproject.path = path
        rproject.residual_data = data

        _parse_roo_section(rproject, section)

        return rproject

    def save(self):
        """Save the file to the path specified in self.path"""
        if self.path is None:
            raise ValueError("Unable to save to unspecified path")

        rproject_content = copy.deepcopy(self.residual_data)

        metadata = clean_dict(dataclasses.asdict(self.metadata))
        if len(metadata):
            rproject_content.setdefault("tool", {})["roo"] = metadata

        sources = clean_list(
            [clean_dict(dataclasses.asdict(source))
             for source in self.sources]
        )

        if len(sources):
            rproject_content.setdefault(
                "tool", {}).setdefault(
                "roo", {})["source"] = sources

        for category in self.ALL_DEPENDENCY_CATEGORIES:
            if category == "main":
                key = "dependencies"
            else:
                key = f"{category}-dependencies"

            deps_data: Dict[str, Union[Dict, str]] = {}
            for d in self.dependencies_for_category(category):
                if d.vcs_spec is not None:
                    deps_data[d.name] = clean_dict(
                        dataclasses.asdict(d.vcs_spec)
                    )
                else:
                    deps_data[d.name] = str(d.constraint)

            if len(deps_data):
                rproject_content.setdefault(
                    "tool", {}).setdefault(
                    "roo", {})[key] = deps_data

        with atomicwrites.atomic_write(self.path,
                                       encoding="utf-8",
                                       overwrite=True) as f:
            toml.dump(rproject_content, f)


def _parse_roo_section(rproject: RProject, section: dict):
    """
    Parses the relevant section from the data, and populates the
    rproject instance
    """
    rproject.metadata = Metadata.fromdict(section)

    sources = rproject.sources

    for source in section.get("source", []):
        sources.append(
            Source.fromdict(source)
        )

    dependencies = rproject.dependencies

    for category in RProject.ALL_DEPENDENCY_CATEGORIES:
        deps = _dependencies_for_category(section, category)
        dependencies.extend(deps)


def _dependencies_for_category(roo_section: dict, category: str) -> list:
    """
    Returns all the dependencies for a given category in the dictionary section
    """
    if category == "main":
        key = "dependencies"
    else:
        key = f"{category}-dependencies"

    deps: List[Dependency] = []
    try:
        filedeps = roo_section[key]
    except KeyError:
        return deps

    for name, value in filedeps.items():
        vcs_spec: Optional[VCSSpec]
        if isinstance(value, dict):
            if value.get("git") is None:
                raise ParsingError(
                    f"A VCS specification in {name} is missing the git key to "
                    "indicate the URL of the git repo"
                )
            vcs_spec = VCSSpec(
                git=value["git"],
                branch=value.get("branch"))
            constraint = None
        else:
            vcs_spec = None
            constraint = parse_constraint(value)
        deps.append(
            Dependency(
                name=name,
                constraint=constraint,
                category=category,
                vcs_spec=vcs_spec
            ))

    return deps


def _read_fileobj(fileobj) -> Dict[str, Any]:
    """Parses the file object and returns its content as a dict"""
    try:
        tomldata = cast(Dict[str, Any], toml.load(fileobj))
    except TomlDecodeError as t:
        raise ParsingError(f"Unable to decode rproject.toml file: {t}")
    except Exception as e:
        raise ParsingError("Unable to parse rproject file: "+str(e))

    return tomldata


def _pop_roo_section(data: dict) -> dict:
    """Pops the tool.roo section from the data.
    The data parameter gets modified in the operation"""
    try:
        return cast(dict, data["tool"].pop("roo"))
    except KeyError:
        return {}


def clean_dict(d: dict) -> dict:
    """
    Returns a new dict from the original dict, with all the keys that
    have None, empty dict and empty list values removed from the dict
    """
    return {
        k: v for k, v in d.items() if v
    }


def clean_list(lst: list) -> list:
    """Returns a new list from the original list, with all the keys
    that have None, empty dict or empty list removed from the list"""

    return [
        x for x in lst if x
    ]
