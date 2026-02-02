import uasyncio

from micropython import const

from ...services import logger
from ...drivers.esp01s import esp01s

from . import http


class Network:
    __slots__ = (
        "_logger",
        "_driver",
        "_http_server_requests",
    )

    _logger: logger.Logger
    _driver: esp01s.ESP01S

    _http_server_requests: dict[int, uasyncio.Task]

    def __init__(self) -> None:
        self._logger = logger.get_logger("network")
        self._driver = esp01s.ESP01S(
            on_tcp_connection_data=self.handle_http_server_request,
        )

    async def connect(self, ssid: bytes, password: bytes) -> bool:
        self._logger.info(f'Connecting to wifi network ssid="{ssid.decode()}"')

        if await self._driver.test() == False:
            self._logger.error(
                f"Unable to connect to wifi network, failed to communicate with the ESP01S"
            )

            return False

        if await self._driver.set_wifi_mode(esp01s.WIFI_MODE_STATION) == False:
            self._logger.error(
                f"Unable to connect to wifi network, failed to set ESP01S in WIFI_MODE_STATION"
            )

            return False

        if await self._driver.connect_wifi_access_point(ssid, password) == False:
            self._logger.error(
                f"Unable to connect to wifi network, an unknown error has occurred"
            )

            return False

        self._logger.info(f'Connected to the wifi network ssid="{ssid.decode()}"')
        return True

    async def start_http_server(self, port: int) -> None:
        self._logger.info(f'Starting an HTTP server port="{port}"')

        self._http_server_requests = {}

        await self._driver.set_tcp_server_connection_multiplexing(
            esp01s.SERVER_MULTIPLEXING_MODE_ON
        )

        await self._driver.start_tcp_server(port)

        self._logger.info(f'HTTP server up and running on port="{port}"')

    def handle_http_server_request(
        self,
        connection_id: int,
        data: memoryview,
    ) -> None:
        self._logger.info(f"Processing HTTP request on connection_id={connection_id}")

        request = http.HTTPRequest.parse(data)
        if request == None:
            return

        self._logger.info(f"request method={request.method} path={request.path}")

        response = http.HTTPResponse()
        context = http.HTTPContext(
            connection_id,
            request,
            response,
        )

        if connection_id in self._http_server_requests:
            return

        self._http_server_requests[connection_id] = uasyncio.create_task(
            self.process_http_server_request(context),
        )

    async def process_http_server_request(
        self,
        context: http.HTTPContext,
    ) -> None:
        try:
            # @TODO: implement the sending of the response
            await self._driver.send_tcp_server_connection_data(
                context.connection_id,
                memoryview(bytes()),
            )
        finally:
            self._http_server_requests.pop(
                context.connection_id,
                None,
            )

    async def run(self) -> None:
        while True:
            # Poll the ESP01S for new data
            await self._driver.poll()

    async def shutdown(self) -> None:
        await self._driver.stop_tcp_server()
        await self._driver.disconnect_wifi_access_point()
