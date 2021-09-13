import pathlib

from typing import Optional
import git


def vcs_clone_shallow(type: str, url: str, ref: Optional[str],
                      dest_dir: pathlib.Path):
    """Clones a repository and puts the result in dest_dir.
    If possible, the cloning is shallow to reduce the transfer amount.
    """
    if dest_dir.exists():
        raise FileExistsError("Cannot clone on an existing directory")

    if type == "git":
        _git_clone_shallow(url, ref, dest_dir)
    else:
        raise ValueError(f"Unable to handle VCS source type {type}")


def _git_clone_shallow(url: str, ref: Optional[str], dest_dir: pathlib.Path):
    """Does the clone for git"""
    if ref is not None:
        git.Repo.clone_from(url, dest_dir, branch=ref, depth=1)
    else:
        git.Repo.clone_from(url, dest_dir, depth=1)
