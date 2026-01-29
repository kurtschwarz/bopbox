import time
import uasyncio

from .services import logger, network


class BopBox:
    __slots__ = ("_tasks", "_logger", "_network")

    _tasks: list[uasyncio.Task]

    _logger: logger.Logger
    _network: network.Network

    def __init__(self) -> None:
        self._tasks = []
        self._logger = logger.get_logger("bopbox")
        self._network = network.Network()

    async def run(self) -> None:
        # Start async tasks
        self._tasks.append(uasyncio.create_task(self._network.run()))

        # Attempt to connect to WiFi
        await self._network.connect(ssid=b"Malicious Toasters", password=b"beep boop")

        # Wait for all tasks to complete
        await uasyncio.gather(*self._tasks)

    async def shutdown(self) -> None:
        self._logger.info("Shutting down")

        await self._network.shutdown()

        return None
