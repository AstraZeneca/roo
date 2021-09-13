from roo.parsing_utils import split_deps_string, split_constraint_string


def test_split_deps_string():
    assert split_deps_string("foo (>=1.2.3)") == [("foo", [">=1.2.3"])]
    assert split_deps_string("data.table (>=1.2.3, <2.0.0)") == [
        ("data.table", [">=1.2.3", "<2.0.0"])]
    assert split_deps_string("data.table") == [("data.table", [])]
    assert split_deps_string("data.table (1.2.3)") == [
        ("data.table", ["==1.2.3"])]
    assert split_deps_string("data.table (==1.2.3)") == [
        ("data.table", ["==1.2.3"])]


def test_split_constraint_string():
    assert split_constraint_string("1.2.3") == ["==1.2.3"]
    assert split_constraint_string(">=1.2.3, <4.5.0, 4.5.6") == [
        ">=1.2.3", "<4.5.0", "==4.5.6"]
