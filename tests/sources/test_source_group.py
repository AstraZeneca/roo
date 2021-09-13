from roo.parsers.rproject import Source
from roo.sources.remote_source import RemoteSource
from roo.sources.source_group import SourceGroup, \
    create_source_group_from_config_list


def test_source_group():
    group = SourceGroup()
    repo = RemoteSource(name="foo", url="xxx", proxy="xxx")
    group.add_source(repo)

    assert len(group.all_sources) == 1
    assert group.source_by_name("foo") == repo


def test_create_source_group_from_config():
    config = [
        Source(name="foo", url="xxx", proxy="xxx"),
        Source(name="bar", url="xxx", proxy="xxx")
    ]

    group = create_source_group_from_config_list(config)

    assert len(group.all_sources) == 2
