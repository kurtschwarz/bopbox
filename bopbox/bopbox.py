import time
import uasyncio

from .config import config
from .services import logger, network, nfc


class BopBox:
    __slots__ = (
        "_tasks",
        "_logger",
        "_network",
        "_nfc",
    )

    _tasks: list[uasyncio.Task]

    _logger: logger.Logger
    _network: network.Network
    _nfc: nfc.NFC

    def __init__(self) -> None:
        self._tasks = []
        self._logger = logger.get_logger("bopbox")
        self._network = network.Network()
        self._nfc = nfc.NFC()

    async def run(self) -> None:
        # Start async tasks
        self._tasks.append(uasyncio.create_task(self._network.run()))
        self._tasks.append(uasyncio.create_task(self._nfc.run()))

        # Attempt to connect to WiFi
        if config.wifi_ssid and config.wifi_password:
            await self._network.connect(
                ssid=config.wifi_ssid.encode(),
                password=config.wifi_password.encode(),
            )

        if config.http_server_enabled and config.http_server_port:
            await self._network.start_http_server(
                port=config.http_server_port,
            )

        # Wait for all tasks to complete
        await uasyncio.gather(*self._tasks)

    async def shutdown(self) -> None:
        self._logger.info("Shutting down")

        # Attempt to disconnect from WiFi (if connected)
        await self._network.shutdown()
        # Shut down the NFC reader
        await self._nfc.shutdown()

        # Cancel all running tasks
        for task in self._tasks:
            task.cancel()

        self._logger.info("Shutdown complete")
        return None
