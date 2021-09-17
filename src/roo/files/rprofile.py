import pathlib
import re
from typing import Union

from atomicwrites import atomic_write


def rprofile_current_environment(
        rprofile_path: pathlib.Path) -> Union[str, None]:
    """
    Gets the currently activated environment as defined in the current
    Rprofile file. If the file does not exist, or no environment is activated,
    returns None

    Args:
        rprofile_path: the path to the Rprofile file

    Returns: the name of the activated environment or None

    """
    if not rprofile_path.exists():
        return None

    with open(rprofile_path, "r", encoding="utf-8") as f:
        content = f.readlines()

    value = _find_rprofile_marker_zone(content)

    if value is None:
        return None

    start, stop = value

    env_name = None
    for line in content[start:stop+1]:
        m = re.match(r"^enabled_env\s*<-\s*\"(\w+)\"", line)
        if m:
            env_name = m.group(1)

    return env_name


def rprofile_set_environment(
        rprofile_path: pathlib.Path, env_name: Union[str, None]) -> None:
    """
    Sets a given environment as enabled in a given rprofile
    path. If the rprofile path does not exists, it will be
    created. If it does exist, a chunk of code will be added
    to the end of the file itself. The previous enabled environment
    will be removed.

    Args:
        rprofile_path: the path to the Rprofile file
        env_name: the name of the environment to activate. If None,
                  no environment will be activated.
    """

    content = []
    if rprofile_path.exists():
        with open(rprofile_path, "r", encoding="utf-8") as f:
            content = f.readlines()

    value = _find_rprofile_marker_zone(content)

    if value is not None:
        start, stop = value
        content[start:stop+1] = []

    if env_name is not None:
        content.extend([
            "# >>> created by roo\n",
            f'enabled_env <- "{env_name}"\n',
            'source(file.path(".envs", enabled_env, "init.R"))\n',
            "# <<< created by roo\n"
        ])

    with atomic_write(rprofile_path, overwrite=True) as f:  # type: ignore
        f.writelines(content)


def _find_rprofile_marker_zone(content: list) -> Union[tuple, None]:
    """
    Find the start and stop index of the last occurrence of the
    roo added section, and return them as a tuple. If it cannot find
    any section, returns None
    """
    start_pos = None
    end_pos = None

    for idx, line in enumerate(content):
        if line.startswith("# >>> created by roo"):
            if start_pos is not None:
                end_pos = None
            start_pos = idx
        elif line.startswith("# <<< created by roo"):
            if start_pos is None:
                continue
            end_pos = idx

    if start_pos is None or end_pos is None:
        return None

    return start_pos, end_pos
