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


def test_source_group_priorities():
    group = SourceGroup()
    repo0 = RemoteSource(name="repo0", url="xxx", proxy="xxx", priority=0)
    repo1 = RemoteSource(name="repo1", url="xxx", proxy="xxx", priority=0)
    repo2 = RemoteSource(name="repo2", url="xxx", proxy="xxx", priority=1)
    repo3 = RemoteSource(name="repo3", url="xxx", proxy="xxx", priority=1)
    group.add_source(repo0)
    group.add_source(repo1)
    group.add_source(repo2)
    group.add_source(repo3)

    sources = group._sources_by_priority()
    assert sources[0][0] == repo0
    assert sources[0][1] == repo1

    assert sources[1][0] == repo2
    assert sources[1][1] == repo3
