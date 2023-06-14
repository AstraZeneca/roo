from roo.resolver import Resolver
from roo.deptree.dependencies import RootDependency, \
    UnresolvedConstrainedDependency
from roo.semver import parse_constraint
from roo.sources.remote_source import RemoteSource
from roo.sources.source_group import SourceGroup


def test_resolver(fixture_file):
    source_group = SourceGroup()
    source_group.add_source(
        RemoteSource(
            name="CRAN",
            url="http://cloud.r-project.org/")
    )

    resolver = Resolver(source_group)
    root = RootDependency(
        dependencies=[
            UnresolvedConstrainedDependency(
                name="stringr",
                constraint=parse_constraint("1.5.0"),
                categories=["main"]
            )
        ]
    )

    resolver.resolve_full_tree(root)
