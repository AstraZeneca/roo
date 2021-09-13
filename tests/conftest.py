import contextlib
import os
import pathlib

import pytest

FIXTURE_DIR = pathlib.Path(os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures'
))


@pytest.fixture
def fixture_file():
    def _fixture_file(*args):
        return pathlib.Path(os.path.join(FIXTURE_DIR, *args))
    return _fixture_file


@contextlib.contextmanager
def chdir(path: pathlib.Path):
    curpath = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(curpath)
