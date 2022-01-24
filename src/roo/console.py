from rich.console import Console
from rich.theme import Theme

_console = None


def init_console(quiet: bool):
    global _console
    if _console is None:
        _console = Console(theme=_create_theme(), quiet=quiet)


def console():
    if _console is None:
        init_console(False)

    return _console


def _create_theme():
    return Theme({
        "success": "green",
        "message": "bold blue",
        "warning": "bold yellow",
        "error": "bold red",
        "package": "turquoise4",
        "version": "yellow",
        "environment": "purple",
    })
