import pathlib

import pytest
from roo.parsers.exceptions import ParsingError
from roo.parsers.rproject import RProject, Source, Dependency, VCSSpec
from roo.semver import Version, parse_constraint


def test_rproject_parsing(fixture_file):
    rproject = RProject.parse(pathlib.Path(
        fixture_file("simple", "rproject.toml")))

    assert len(rproject.dependencies) == 2
    assert len(rproject.dependencies_for_category("main")) == 1
    assert len(rproject.dependencies_for_category("dev")) == 1
    assert rproject.dependencies_for_category("main")[0].constraint == \
        Version.parse("0.4.2")

    assert len(rproject.sources) == 2
    assert rproject.content_hash == \
        '737c399d1a307e03002f7c4e2fa9908bec5afabeaf0663743d1afd384bbd1100'
    assert rproject.metadata
    assert rproject.metadata.name is None
    assert rproject.metadata.version is None
    assert rproject.metadata.env_id is None
    assert rproject.metadata.authors == []
    assert rproject.metadata.maintainers == []
    assert rproject.metadata.title is None
    assert rproject.metadata.description is None


def test_metadata(fixture_file):
    rproject = RProject.parse(
        pathlib.Path(fixture_file("simple", "rproject_metainfo.toml")))

    assert rproject.metadata.name == "mytool"
    assert rproject.metadata.version == "0.1.0"
    assert rproject.metadata.env_id == "ENV-0000"
    assert rproject.metadata.authors == ["Author"]
    assert rproject.metadata.title == "This is my tool"
    assert rproject.metadata.description == ("There are many other like "
                                             "this but this one is mine")
    assert rproject.metadata.maintainers == ["Maintainer"]


def test_toml_duplicate_keys(fixture_file):
    with pytest.raises(ParsingError):
        RProject.parse(fixture_file("simple", "rproject_dup.toml"))


def test_rproject_vcs_info(fixture_file):
    rproject = RProject.parse(fixture_file("git", "rproject.toml"))

    deps = rproject.dependencies_for_category("main")

    assert deps[0].vcs_spec is None
    assert str(deps[0].constraint) == "3.2-7"

    assert (
        deps[1].vcs_spec == VCSSpec(
            git="https://github.com/AstraZeneca/qscheck.git",  # noqa
            branch=None))
    assert deps[1].constraint is None


def test_rproject_new_file(tmpdir):
    rproject = RProject()
    rproject.path = pathlib.Path(tmpdir) / "rproject.toml"
    rproject.save()

    with open(rproject.path, "r", encoding="utf-8") as f:
        assert f.read() == ""

    rproject.metadata.name = "mytool"
    rproject.metadata.version = "0.1.0"
    rproject.metadata.env_id = "ENV-0000"
    rproject.metadata.authors = ["Author"]
    rproject.metadata.title = "This is my tool"
    rproject.metadata.description = ("There are many other like "
                                     "this but this is mine")
    rproject.metadata.maintainers = ["Maintainer"]

    rproject.sources.append(Source(
        name="CRAN",
        url="http://example.com/CRAN"
    ))

    rproject.dependencies.append(
        Dependency(name="foo",
                   constraint=parse_constraint(">1.2.0"),
                   category="main",
                   vcs_spec=None
                   )
    )

    rproject.dependencies.append(
        Dependency(name="bar",
                   constraint=parse_constraint("1.2.0"),
                   category="main",
                   vcs_spec=None
                   )
    )

    rproject.dependencies.append(
        Dependency(name="baz",
                   constraint=parse_constraint("1.2.0"),
                   category="dev",
                   vcs_spec=None
                   )
    )

    rproject.save()
    with open(rproject.path, "r", encoding="utf-8") as f:
        assert f.read() == """[tool.rip]
name = \"mytool\"
version = \"0.1.0\"
authors = [ "Author",]
maintainers = [ "Maintainer",]
env_id = \"ENV-0000\"
title = \"This is my tool\"
description = \"There are many other like this but this is mine\"
[[tool.rip.source]]
name = "CRAN"
url = "http://example.com/CRAN"

[tool.rip.dependencies]
foo = ">1.2.0"
bar = "1.2.0"

[tool.rip.dev-dependencies]
baz = "1.2.0"
"""
