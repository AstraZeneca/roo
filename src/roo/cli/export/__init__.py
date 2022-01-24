import click
from roo.cli.lock import _ensure_lock
from roo.exporters.lock.base_exporter import BaseExporter
from roo.exporters.lock.lock_csv_exporter import LockCSVExporter
from roo.exporters.lock.lock_packrat_exporter import LockPackratExporter


@click.group(help="Commands to export data and information to different tools")
def export():
    pass


@export.command(name="lock", help="Exports lock to different formats")
@click.argument("format", type=click.Choice(["csv", "packrat"]))
@click.argument("output", type=click.Path(writable=True))
def export_lock(format, output):
    lock_file = _ensure_lock(False, False)

    exporter: BaseExporter
    if format == "csv":
        exporter = LockCSVExporter()
    elif format == "packrat":
        exporter = LockPackratExporter()
    else:
        raise RuntimeError(f"Programming error. Not matched format {format}")

    exporter.export(lock_file, output)
