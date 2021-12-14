import pathlib

from roo.files.rprofile import RProfile
import textwrap

from roo.files.rprofile import _find_rprofile_marker_zone


def test_rprofile_set_environment_with_existent_file(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write("# A comment\n")

    RProfile(rprofile_path).enabled_environment = "foobar"

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # A comment
    # >>> created by roo
    enabled_env <- "foobar"
    source(file.path(".envs", enabled_env, "init.R"))
    # <<< created by roo
    """)


def test_rprofile_set_environment_from_nonexistent_file(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    RProfile(rprofile_path).enabled_environment = "foobar"

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # >>> created by roo
    enabled_env <- "foobar"
    source(file.path(".envs", enabled_env, "init.R"))
    # <<< created by roo
    """)


def test_rprofile_set_environment_with_already_present_env(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # >>> created by roo
            enabled_env <- "foobar"
            source(file.path(".envs", enabled_env, "init.R"))
            # <<< created by roo
            # This is a comment after the old entry
            """))

    RProfile(rprofile_path).enabled_environment = "barbaz"

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # This is comment before the old entry
    # This is a comment after the old entry
    # >>> created by roo
    enabled_env <- "barbaz"
    source(file.path(".envs", enabled_env, "init.R"))
    # <<< created by roo
    """)


def test_rprofile_set_environment_to_none(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # >>> created by roo
            enabled_env <- "foobar"
            source(file.path(".envs", enabled_env, "init.R"))
            # <<< created by roo
            # This is a comment after the old entry
            """))

    RProfile(rprofile_path).enabled_environment = None

    with open(rprofile_path) as f:
        content = f.read()

    assert content == textwrap.dedent("""\
    # This is comment before the old entry
    # This is a comment after the old entry
    """)


def test_rprofile_current_environment(tmpdir):
    rprofile_path = pathlib.Path(tmpdir, ".Rprofile")

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # >>> created by roo
            enabled_env <- "foobar"
            source(file.path(".envs", enabled_env, "init.R"))
            # <<< created by roo
            # This is a comment after the old entry
            """))

    assert RProfile(rprofile_path).enabled_environment == "foobar"

    with open(rprofile_path, "w") as f:
        f.write(textwrap.dedent("""\
            # This is comment before the old entry
            # This is a comment after the old entry
            """))

    assert RProfile(rprofile_path).enabled_environment is None


def test_find_rprofile_marker_zone():
    content = textwrap.dedent("""\
        # This is comment before the old entry
        # >>> created by roo
        enabled_env <- "foobar"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by roo
        # This is a comment after the old entry
        """).splitlines()

    assert _find_rprofile_marker_zone(content) == (1, 4)
    assert _find_rprofile_marker_zone([]) is None

    content = textwrap.dedent("""\
        # This is comment before the old entry
        # >>> created by roo
        enabled_env <- "foobar"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by roo
        # This is a comment after the old entry
        # >>> created by roo
        enabled_env <- "barbaz"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by roo
        # This is the second end
        """).splitlines()

    assert _find_rprofile_marker_zone(content) == (6, 9)

    content = textwrap.dedent("""\
        # This is comment before the old entry
        # >>> created by roo
        enabled_env <- "foobar"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by roo
        # This is a comment after the old entry
        # >>> created by roo
        enabled_env <- "barbaz"
        source(file.path(".envs", enabled_env, "init.R"))
        # This is the second end
        """).splitlines()

    assert _find_rprofile_marker_zone(content) is None

    content = textwrap.dedent("""\
        # Finds and end before a start
        # <<< created by roo
        # >>> created by roo
        enabled_env <- "barbaz"
        source(file.path(".envs", enabled_env, "init.R"))
        # <<< created by roo
        # This is the second end
        """).splitlines()

    assert _find_rprofile_marker_zone(content) == (2, 5)
