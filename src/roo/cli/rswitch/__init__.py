import click
from click.exceptions import Exit
import platform

from roo.console import console
from roo.environment import find_all_installed_r_homes


@click.command(
    help="Switches the system wide R version.\n\n"
         "This command works only on macOS. "
         "On other platforms it will do nothing."
)
@click.argument("version", type=click.STRING, required=False)
def rswitch(version):
    if not _on_macos():
        console().print(
            "[warning]rswitch subcommand only works on macOS."
            " Nothing to do.[/warning]"
        )
        raise Exit(0)

    all_r_homes = find_all_installed_r_homes()

    if version is None:
        _print_available(all_r_homes)
        raise Exit(0)

    try:
        found_version = [x for x in all_r_homes if x["version"] == version][0]
    except IndexError:
        console().print(f"[error]Version {version} not found.[/error]")
        _print_available(all_r_homes)
        raise Exit(1)

    if found_version["active"]:
        console().print(
            f"Version [version]{version}[/version] already active."
        )
        return

    current_link = found_version["home_path"] / ".." / "Current"
    if not current_link.is_symlink():
        console().print(
            f"[error]Entry {current_link} is supposed to be a link, but it "
            "is not. Check your R installation.[/error]"
        )
        raise click.ClickException(f"{current_link} is not a link.")

    try:
        current_link.unlink(missing_ok=True)
    except Exception as e:
        console().print(
            f"[error]Unable to unlink {current_link}. You might "
            "not have permissions to do so. Check your R installation."
            "[/error]"
        )
        raise click.ClickException(f"Cannot unlink {current_link}: {e}")

    try:
        current_link.symlink_to(found_version["home_path"])
    except Exception:
        console().print(
            f"[error]"
            f"Unable to link {current_link} to {found_version['home_path']}."
            "[/error]"
        )
        console().print(
            "[error]"
            "Note: your R installation may now not work anymore and the link "
            "have to be restored manually.[/error]"
        )
        raise click.ClickException(f"Cannot unlink {current_link}.")

    console().print(
        f"R Version [version]{found_version['version']}[/version] activated."
    )


def _on_macos() -> bool:
    return platform.system() == "Darwin"


def _print_available(all_r_homes):
    console().print("Available versions:")
    for entry in all_r_homes:
        console().print(
            ("* " if entry["active"] else "  ") +
            f"[version]{entry['version']}[/version] {entry['home_path']}"
        )
