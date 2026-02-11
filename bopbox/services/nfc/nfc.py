import uasyncio

from micropython import const

from ...services import logger
from ...drivers.pn532 import pn532


class NFC:
    __slots__ = (
        "_logger",
        "_driver",
    )

    _logger: logger.Logger
    _driver: pn532.PN532

    def __init__(self) -> None:
        self._logger = logger.get_logger("nfc")
        self._driver = pn532.PN532()

    async def run(self) -> None:
        self._logger.debug("running")

        while True:
            # Poll the PN532 for new data
            await self._driver.receive()

    async def shutdown(self) -> None:
        self._logger.debug("shutting down")
