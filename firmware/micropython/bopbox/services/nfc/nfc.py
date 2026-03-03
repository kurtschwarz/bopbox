import uasyncio

from micropython import const

from ...services import logger
from ...drivers.pn532 import pn532


class NFC:
    __slots__ = (
        "_logger",
        "_driver",
        "_current_card_uid",
    )

    _logger: logger.Logger
    _driver: pn532.PN532

    _receive_data_task: uasyncio.Task
    _detect_card_task: uasyncio.Task

    _current_card_uid: bytes | None

    def __init__(self) -> None:
        self._logger = logger.get_logger("nfc")
        self._driver = pn532.PN532()
        self._current_card_uid = None

    async def _receive_data(self) -> None:
        while True:
            await self._driver.receive()
            await uasyncio.sleep_ms(100)

    async def _detect_card(self) -> None:
        while True:
            uid = await self._driver.get_passive_target()
            if uid is None and self._current_card_uid is not None:
                self._current_card_uid = None
            elif uid and self._current_card_uid != uid:
                self._current_card_uid = uid
                self._logger.debug(f"detected card uid={[hex(i) for i in uid]}")

            await uasyncio.sleep_ms(100)

    async def run(self) -> None:
        self._logger.debug("running")

        self._receive_data_task = uasyncio.create_task(self._receive_data())
        self._detect_card_task = uasyncio.create_task(self._detect_card())

        await uasyncio.gather(self._receive_data_task, self._detect_card_task)

    async def startup(self) -> None:
        self._logger.info("starting up")

        await self._driver.wake_up()
        await self._driver.sam_config()
        await self._driver.set_retries()

        self._logger.info("startup complete")

    async def shutdown(self) -> None:
        self._logger.debug("shutting down")

        self._detect_card_task.cancel()
        self._receive_data_task.cancel()

        self._logger.info("shutdown complete")
