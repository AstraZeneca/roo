import re
from typing import List, Tuple


def split_constraint_string(constraint_string: str) -> List[str]:
    """
    Splits a constraint string such as

    >=1.2.3, <4.0.0, 3.5.0

    into its subparts, and returns a list of strings.
    Notation such as exact match 3.5.0 will be converted to ==3.5.0
    """

    constraint: List[str] = []
    prefixes = (">=", ">", "<", "<=", "==")
    constraint_string = constraint_string.strip()
    if len(constraint_string) == 0:
        return constraint

    try:
        constraint = [x.strip() for x in constraint_string.split(',')]
        constraint = [x
                      if x.startswith(prefixes) else "=="+x
                      for x in constraint]
    except Exception:
        raise ValueError(
            f"Unable to parse dependency string: {constraint_string}")

    return constraint


def split_deps_string(string: str) -> List[Tuple]:
    """
    Splits a dependency string such as

    foo (>=1.2.3, <4.0.0), bar (3.5.0)

    into its subparts, and returns a list of tuples. In each tuple the first
    element is the name, the second the list of constraint.
    Notation such as 3.5.0 will be converted to ==3.5.0
    """

    result: List[Tuple] = []
    try:
        for entry in re.findall(r"([a-zA-Z0-9_\\.]+)\s*(\(.*?\))?", string):
            name = entry[0].strip()
            constraint = split_constraint_string(
                entry[1].strip().strip("()"))
            result.append((name, constraint))
    except Exception:
        raise ValueError(f"Unable to parse dependency string: {string}")

    return result
