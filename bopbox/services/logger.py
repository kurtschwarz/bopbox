import sys

from micropython import const

DEBUG = const(0)
INFO = const(1)
WARN = const(2)
ERROR = const(3)

_LEVEL_NAMES = {DEBUG: "DEBUG", INFO: "INFO", WARN: "WARN", ERROR: "ERROR"}

_loggers: dict[str, "Logger"] = {}

_stdout = sys.stdout
_stderr = sys.stderr


def get_logger(scope: str = "root", level: int = INFO) -> "Logger":
    """Get or create a logger for the given scope."""
    if scope not in _loggers:
        _loggers[scope] = Logger(scope, level)

    return _loggers[scope]


class Logger:
    __slots__ = ("_scope", "_level", "_level_name")

    _scope: str
    _level: int
    _level_name: str

    def __init__(self, scope: str = "root", level: int = INFO) -> None:
        self._scope = scope.upper()
        self._level = level
        self._level_name = _LEVEL_NAMES.get(level) or "UNKNOWN"

    def _log(self, level: int, msg: str) -> None:
        if level >= self._level:
            stream = sys.stderr if level == ERROR else sys.stdout
            stream.write(f"[{self._scope}][{self._level_name}] {msg}\n")

    def debug(self, msg: str) -> None:
        self._log(DEBUG, msg)

    def info(self, msg: str) -> None:
        self._log(INFO, msg)

    def warn(self, msg: str) -> None:
        self._log(WARN, msg)

    def error(self, msg: str) -> None:
        self._log(ERROR, msg)
