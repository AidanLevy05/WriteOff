import os
import sys


class Colors:
    def __init__(self, enabled: bool | None = None) -> None:
        self.enabled = should_enable_color() if enabled is None else enabled

    def _wrap(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def heading(self, text: str) -> str:
        return self._wrap(text, "1;36")

    def good(self, text: str) -> str:
        return self._wrap(text, "32")

    def danger(self, text: str) -> str:
        return self._wrap(text, "31")

    def warning(self, text: str) -> str:
        return self._wrap(text, "33")

    def reputation(self, text: str) -> str:
        return self._wrap(text, "35")

    def muted(self, text: str) -> str:
        return self._wrap(text, "90")

    def selected(self, text: str) -> str:
        return self._wrap(text, "7")


def should_enable_color() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ
