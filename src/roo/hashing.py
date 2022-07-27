import pathlib
import hashlib
import re


def sha256path(filename: str) -> str:
    """
    Computes the sha256 of a given file

    Args:
        filename: the filename

    Returns: the sha256

    """
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def md5path(filename: pathlib.Path) -> str:
    """
    Computes the md5 of a given file

    Args:
        filename: the filename

    Returns: the md5

    """
    md5_hash = hashlib.md5()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
        return md5_hash.hexdigest()


def validate_hash(value: str) -> bool:
    """Validates the format of a hash. Returns true if the hash is properly
    formatted. False otherwise."""
    m = re.match("[a-zA-Z0-9]+:[a-fA-F0-9]+", value)
    return m is not None


def validate_md5(value: str):
    """
    Validates the format of an md5. Returns True if the md5 is properly
    formatted. False otherwise.
    """
    m = re.match("[A-Fa-f0-9]{32}", value)
    return m is not None
