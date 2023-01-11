import pathlib
import shutil
from rich.columns import Columns
from roo.caches.source_cache import all_source_caches
from roo.caches.build_cache import all_build_caches

import click
from roo.console import console


@click.group(help="Commands to interact with the cache")
def cache():
    pass


@cache.command(name="clear", help="Clear the cache completely")
def cache_clear():
    cache_root_dir = pathlib.Path("~/.roo/cache").expanduser()
    console().print("Clearing cache")
    try:
        shutil.rmtree(cache_root_dir)
        cache_root_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise click.ClickException(f"Unable to clear cache: {e}")


@cache.command(
    name="remove",
    help=(
        "Removes one specific package from the cache. Specifically, it removes"
        " the source code and any built package. If the package is found in "
        " multiple sources, it will be removed from all of them."
    )
)
@click.argument("package", type=click.STRING)
def cache_remove(package):
    source_caches = all_source_caches()
    for c in source_caches:
        console().print(
            f"Removing [package]{package}[/package] from source cache of "
            f"[source]{c.source_url}[/source]"
        )
        try:
            c.remove_package(package)
        except Exception as e:
            raise click.ClickException(f"Unable to clear package cache: {e}")

    build_caches = all_build_caches()

    for c in build_caches:
        console().print(
            f"Removing [package]{package}[/package] from build cache"
        )
        try:
            c.clear_build(package)
        except Exception as e:
            raise click.ClickException(f"Unable to clear package cache: {e}")


@cache.command(
    name="list",
    help="Lists the content of the cache."
)
def cache_list():
    source_caches = all_source_caches()
    build_caches = all_build_caches()

    for c in source_caches:
        console().print(
            f":earth_africa: Packages cache for source "
            f"[source]{c.source_url}[/source]")

        console().print(Columns(
            [
                f"  :package: [package]{package_name}[/package]"
                for package_name in c.cached_package_names()
            ]
        ))
        console().print()

    build_caches = all_build_caches()

    for c in build_caches:
        console().print(
            f":hammer: Built packages cache for [environment]"
            f"R-{c.r_version}-{c.platform}[/environment]:"
        )

        console().print(Columns(
            [
                f"  :zap: [package]{name} {version}[/package]"
                for name, version in c.list_builds()
            ]
        ))
        console().print()
