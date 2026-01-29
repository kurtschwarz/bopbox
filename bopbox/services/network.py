from micropython import const

from ..services import logger
from ..drivers import esp01s


class Network:
    __slots__ = ("_logger", "_driver")

    _logger: logger.Logger
    _driver: esp01s.ESP01S

    def __init__(self) -> None:
        self._logger = logger.get_logger("network")
        self._driver = esp01s.ESP01S()

    async def connect(self, ssid: bytes, password: bytes) -> bool:
        self._logger.info(f"Connecting to wifi network ssid=\"{ssid.decode()}\"")

        if await self._driver.test() == False:
            self._logger.error(f"Unable to connect to wifi network, failed to communicate with the ESP01S")
            return False

        if await self._driver.set_wifi_mode(esp01s.WIFI_MODE_STATION) == False:
            self._logger.error(f"Unable to connect to wifi network, failed to set ESP01S in WIFI_MODE_STATION")
            return False

        if await self._driver.connect_wifi_access_point(ssid, password) == False:
            self._logger.error(f"Unable to connect to wifi network, an unknown error has occurred")
            return False

        self._logger.info(f"Connected to the wifi network ssid=\"{ssid.decode()}\"")
        return True

    async def start_http_server(self, port: int) -> None:
        self._logger.info(f"Starting an HTTP server port=\"{port}\"")

        await self._driver.set_tcp_server_connection_multiplexing(esp01s.SERVER_MULTIPLEXING_MODE_ON)
        await self._driver.start_tcp_server(port)

        self._logger.info(f"HTTP server up and running on port=\"{port}\"")

    async def run(self) -> None:
        while True:
            # Poll the ESP01S for new data
            await self._driver.poll()

    async def shutdown(self) -> None:
        await self._driver.stop_tcp_server()
        await self._driver.disconnect_wifi_access_point()
