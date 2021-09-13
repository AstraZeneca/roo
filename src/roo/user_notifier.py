import abc
from rich.console import Console
from rich.theme import Theme


class NotifierABC(abc.ABC):
    """ABC for notifiers"""
    @abc.abstractmethod
    def message(self, message: str, indent: int = 0):
        pass

    @abc.abstractmethod
    def warning(self, message: str):
        pass

    @abc.abstractmethod
    def error(self, message: str):
        pass


class UserNotifier(NotifierABC):
    """
    Class that prints a statement out unless option 'quiet' is chosen
    """

    def __init__(self, quiet=False, console=None):
        self.quiet = quiet
        if console is None:
            console = Console(theme=self._create_theme())

        self._console = console

    def message(self, message, indent=0):
        if not self.quiet:
            self._console.print(" "*indent + message.strip())

    def error(self, message: str):
        self.message(f"[error]{message}[/error]")

    def warning(self, message: str):
        self.message(f"[warning]{message}[/warning]")

    def _create_theme(self):
        return Theme({
            "success": "green",
            "warning": "bold yellow",
            "error": "bold red",
            "package": "turquoise4",
            "version": "yellow",
            "environment": "purple",
        })


class NullNotifier(NotifierABC):
    """Notifier that shows nothing"""

    def message(self, message: str, indent: int = 0):
        pass

    def error(self, message: str):
        pass

    def warning(self, message: str):
        pass
