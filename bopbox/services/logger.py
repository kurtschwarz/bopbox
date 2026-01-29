import sys

from micropython import const

DEBUG = const(0)
INFO = const(1)
WARN = const(2)
ERROR = const(3)

_LEVEL_NAMES = {DEBUG: "DEBUG", INFO: "INFO", WARN: "WARN", ERROR: "ERROR"}

_loggers: dict[str, "Logger"] = {}

_stream_stdout = sys.stdout
_stream_stderr = sys.stderr


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

    def _log(self, level: int, message: str) -> None:
        if level >= self._level:
            stream = _stream_stderr if level == ERROR else _stream_stdout
            stream.write(f"[{self._scope}][{self._level_name}] {message}\n")

    def debug(self, message: str) -> None:
        self._log(DEBUG, message)

    def info(self, message: str) -> None:
        self._log(INFO, message)

    def warn(self, message: str) -> None:
        self._log(WARN, message)

    def error(self, message: str) -> None:
        self._log(ERROR, message)
