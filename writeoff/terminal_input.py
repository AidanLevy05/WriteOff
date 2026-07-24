import os
import sys
from dataclasses import dataclass


UP = "UP"
DOWN = "DOWN"
LEFT = "LEFT"
RIGHT = "RIGHT"
ENTER = "ENTER"
ESCAPE = "ESCAPE"
QUIT = "QUIT"
SAVE = "SAVE"
LOAD = "LOAD"
HELP = "HELP"
TAB = "TAB"
CHARACTER = "CHARACTER"


@dataclass(frozen=True)
class Key:
    name: str
    value: str = ""


class TerminalInput:
    def __init__(self) -> None:
        self._old_settings = None
        self._is_windows = os.name == "nt"

    def __enter__(self) -> "TerminalInput":
        if self._is_windows:
            return self
        if sys.stdin.isatty():
            import termios
            import tty

            self._old_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.restore()

    def restore(self) -> None:
        if self._old_settings is None or self._is_windows:
            return
        import termios

        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)
        self._old_settings = None

    def read_key(self) -> Key:
        if self._is_windows:
            return self._read_windows()
        return self._read_posix()

    def _read_windows(self) -> Key:
        import msvcrt

        char = msvcrt.getwch()
        if char in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            return {
                "H": Key(UP),
                "P": Key(DOWN),
                "K": Key(LEFT),
                "M": Key(RIGHT),
            }.get(code, Key(CHARACTER, code))
        return _semantic_char(char)

    def _read_posix(self) -> Key:
        data = os.read(sys.stdin.fileno(), 1)
        if not data:
            return Key(QUIT)
        char = data.decode("utf-8", errors="replace")
        if char == "\x1b":
            rest = _read_available(2)
            if rest in {"[A", "OA"}:
                return Key(UP)
            if rest in {"[B", "OB"}:
                return Key(DOWN)
            if rest in {"[D", "OD"}:
                return Key(LEFT)
            if rest in {"[C", "OC"}:
                return Key(RIGHT)
            return Key(ESCAPE)
        return _semantic_char(char)


def _read_available(limit: int) -> str:
    if not sys.stdin.isatty():
        return os.read(sys.stdin.fileno(), limit).decode("utf-8", errors="replace")
    import select

    chars = []
    for _ in range(limit):
        ready, _, _ = select.select([sys.stdin], [], [], 0.08)
        if not ready:
            break
        data = os.read(sys.stdin.fileno(), 1)
        if not data:
            break
        chars.append(data.decode("utf-8", errors="replace"))
    return "".join(chars)


def _semantic_char(char: str) -> Key:
    if char in ("\r", "\n"):
        return Key(ENTER)
    if char == "\x03":
        raise KeyboardInterrupt
    if char == "\x1b":
        return Key(ESCAPE)
    if char == "\t":
        return Key(TAB)
    lowered = char.lower()
    if lowered == "q":
        return Key(QUIT)
    if lowered == "s":
        return Key(SAVE)
    if lowered == "l":
        return Key(LOAD)
    if lowered in {"h", "?"}:
        return Key(HELP)
    return Key(CHARACTER, char)
