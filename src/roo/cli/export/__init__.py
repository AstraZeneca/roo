import click
from roo.console import console
from roo.cli.lock import _ensure_lock
from roo.exporters.exceptions import ExportError
from roo.exporters.lock.base_exporter import BaseExporter
from roo.exporters.lock.lock_csv_exporter import LockCSVExporter
from roo.exporters.lock.lock_packrat_exporter import LockPackratExporter
from roo.exporters.lock.lock_renv_exporter import LockRenvExporter


@click.group(help="Commands to export data and information to different tools")
def export():
    pass


@export.command(name="lock", help="Exports lock to different formats")
@click.argument("format", type=click.Choice(["csv", "packrat", "renv"]))
@click.argument("output", type=click.Path(writable=True), required=False)
def export_lock(format, output):
    lock_file = _ensure_lock(False, False)

    exporter: BaseExporter
    if format == "csv":
        exporter = LockCSVExporter()
        default_filename = "lock.csv"
    elif format == "packrat":
        exporter = LockPackratExporter()
        default_filename = "packrat.lock"
    elif format == "renv":
        exporter = LockRenvExporter()
        default_filename = "renv.lock"
    else:
        raise RuntimeError(f"Programming error. Not matched format {format}")

    if output is None:
        output = default_filename

    try:
        exporter.export(lock_file, output)
    except ExportError as e:
        console().print(f"[error]Unable to export lock file: {e}.[/error]")

    console().print(
        f"[success]Successfully exported lock file to {output}[/success]"
    )
