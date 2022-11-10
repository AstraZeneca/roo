from __future__ import annotations
import dataclasses

import pathlib
import re
import typing
from typing import Dict

from ..parsing_utils import split_deps_string
from .exceptions import ParsingError


@dataclasses.dataclass
class Dependency:
    """
    Describes an abstract dependency found in the package DESCRIPTION file.
    """
    name: str
    constraint: list


class Description:
    """Parses and exposes the data inside a DESCRIPTION file"""

    def __init__(self, package: str, version: str, r_constraint: list,
                 dependencies: typing.List[Dependency]):
        self.package = package
        self.version = version
        self.r_constraint = r_constraint
        self.dependencies = dependencies

    @classmethod
    def parse(cls, fileobj_or_path) -> Description:
        """Parses a DESCRIPTION file. Returns an instance of this class."""
        if isinstance(fileobj_or_path, (str, pathlib.Path)):
            with open(fileobj_or_path, encoding="utf-8") as f:
                data = _parse_fileobj(f)
        else:
            data = _parse_fileobj(fileobj_or_path)

        if "Package" not in data:
            raise ParsingError(
                f"Package unspecified in DESCRIPTION file {fileobj_or_path}")

        if "Version" not in data:
            raise ParsingError(
                f"Version unspecified in DESCRIPTION file {fileobj_or_path}")

        r_constraint = []
        deps = {}
        for key in ("Depends", "Imports", "LinkingTo"):
            if key in data:
                for name, constraint in split_deps_string(data[key]):

                    # Special case. If the dependency is "R" it is a constraint
                    # over the R version and it is treated separately.
                    if name == "R":
                        r_constraint = constraint
                        continue

                    if name not in deps:
                        deps[name] = Dependency(name=name, constraint=[])

                    # The package may be present multiple times. For example,
                    # a dependency may be specified both in Imports and
                    # LinkingTo.
                    # We combine the constraints and make them unique if that's
                    # the case, because they might be different and we have
                    # no idea if they are.
                    deps[name].constraint = sorted(
                        list(set(deps[name].constraint + constraint)))

        return cls(
            package=data["Package"],
            version=data["Version"],
            r_constraint=r_constraint,
            dependencies=list(deps.values())
        )


def _parse_fileobj(fileobj) -> dict:
    """Parses the actual content of the file object"""
    d: Dict[str, str] = {}

    current_keyword = None
    for line in fileobj:
        m_keyword = re.match(r"^(.+?):\s(.*)", line)
        m_continuation = re.match(r"^\s+", line)
        if m_keyword is not None:
            current_keyword = m_keyword.group(1)
            if current_keyword in d.keys():
                raise ParsingError(f"Keyword {current_keyword} has been "
                                   "found twice in the DESCRIPTION file")

            d[current_keyword] = m_keyword.group(2).strip()
        elif m_continuation is not None:
            if current_keyword is None:
                raise ParsingError("Indented line found without preceding"
                                   " keyword")
            d[current_keyword] += " " + line.strip()
        else:
            raise ParsingError(f"Found line with unknown format\n\n{line}")

    return d
