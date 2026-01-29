import time

from .services import logger


class BopBox:
    __slots__ = ("_debug", "_logger")

    _debug: bool
    _logger: logger.Logger

    def __init__(self, debug: bool = False) -> None:
        self._debug = debug
        self._logger = logger.get_logger(
            "bopbox", logger.DEBUG if debug else logger.INFO
        )

    async def run(self) -> None:
        self._logger.info("Running")

        while True:
            time.sleep(1)

    async def shutdown(self) -> None:
        self._logger.info("Shutting down")
        return None
