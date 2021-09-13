from typing import Optional
import tempfile
import shutil
import hashlib
import pathlib
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__file__)


class VCSStore:
    """Store for the VCS clones we perform."""

    def __init__(self, vcs_url: str, root_dir: Optional[pathlib.Path] = None):
        self.vcs_url = vcs_url
        if root_dir is None:
            root_dir = pathlib.Path(tempfile.mkdtemp())

        self.root_dir = root_dir

    @property
    def base_dir(self) -> pathlib.Path:
        """
        Returns the base directory for the cache.
        """
        path = self.root_dir / "vcs"
        path.mkdir(parents=True, exist_ok=True)
        url = urlparse(self.vcs_url)
        return self.root_dir / "vcs" / url.netloc / hashlib.sha256(
            url.path.encode("utf-8")).hexdigest()

    def clone_dir(self, ref: Optional[str]) -> pathlib.Path:
        """Returns the directory where to clone the given ref"""
        if ref is None:
            ref = "HEAD"
        return self.base_dir / ref

    def clear(self):
        """Clear the whole cache."""
        logging.info(f"Clearing all vcs store at {self.base_dir}")
        try:
            shutil.rmtree(self.base_dir)
        except FileNotFoundError:
            pass

    def clear_clone(self, ref: Optional[str]):
        """Clear the specified clone reference. Does nothing if not present"""
        if ref is None:
            ref = "HEAD"

        logging.info(f"Clearing ref {ref}, vcs store at {self.base_dir}")

        try:
            shutil.rmtree(self.clone_dir(ref))
        except FileNotFoundError:
            pass
