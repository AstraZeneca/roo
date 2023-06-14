from roo.parsers.description import Description, Dependency


def test_description_parsing(fixture_file):
    description = Description.parse(fixture_file("DESCRIPTION"))

    assert isinstance(description, Description)
    assert len(description.dependencies) == 4
    assert all([isinstance(x, Dependency) for x in description.dependencies])
    assert description.version == "2.0"
    assert description.package == "abc"
    assert description.r_constraint == ['>= 2.10']


def test_description_with_split_deps(fixture_file):
    description = Description.parse(
        fixture_file("DESCRIPTION_with_split_deps"))
    assert 'rlang' in [d.name for d in description.dependencies]


def test_empty_import(fixture_file):
    description = Description.parse(
        fixture_file("DESCRIPTION_with_empty_imports"))
    assert len(description.dependencies) == 0


def test_duplicated_entries(fixture_file):
    description = Description.parse(
        fixture_file("DESCRIPTION_with_split_deps")
    )

    dep_list = [d for d in description.dependencies if d.name == "Rcpp"]
    assert len(dep_list) == 1
    assert dep_list[0].constraint == ['>= 1.0.1']


def test_incorrect_keyword_identified(fixture_file):
    description = Description.parse(
        fixture_file("DESCRIPTION_incorrect_keyword_identified")
    )

    assert len(description.dependencies) == 5
