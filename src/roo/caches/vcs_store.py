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

    def __init__(self, root_dir: Optional[pathlib.Path] = None):
        if root_dir is None:
            root_dir = pathlib.Path(tempfile.mkdtemp())

        self.root_dir = root_dir

    def base_dir(self, vcs_url: str) -> pathlib.Path:
        """
        Returns the base directory for the cache for a given url
        """
        path = self.root_dir / "vcs"
        path.mkdir(parents=True, exist_ok=True)
        url = urlparse(vcs_url)
        return self.root_dir / "vcs" / url.netloc / hashlib.sha256(
            url.path.encode("utf-8")).hexdigest()

    def clone_dir(self, vcs_url: str, ref: Optional[str]) -> pathlib.Path:
        """Returns the directory where to clone the given ref"""
        if ref is None:
            ref = "HEAD"
        return self.base_dir(vcs_url) / ref

    def clear(self):
        """Clear the whole cache."""
        logging.info(f"Clearing all vcs stores at {self.root_dir}")
        try:
            shutil.rmtree(self.root_dir)
        except FileNotFoundError:
            pass

    def clear_clone(self, vcs_url: str, ref: Optional[str]):
        """Clear the specified clone reference. Does nothing if not present"""
        if ref is None:
            ref = "HEAD"

        logging.info(
            f"Clearing vcs store at {self.root_dir} "
            f"for url {vcs_url} ref {ref}"
        )

        try:
            shutil.rmtree(self.clone_dir(vcs_url, ref))
        except FileNotFoundError:
            pass
