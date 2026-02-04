import machine
import uasyncio

from typing import Callable
from micropython import const

from . import _tcp


_DEFAULT_UART_ID = const(1)
_DEFAULT_UART_TX_PIN = const(20)
_DEFAULT_UART_RX_PIN = const(21)
_DEFAULT_UART_BAUD_RATE = const(115200)
_DEFAULT_UART_TX_BUFFER_LEN = const(1024)
_DEFAULT_UART_RX_BUFFER_LEN = const(_DEFAULT_UART_TX_BUFFER_LEN * 2)

_DEFAULT_CMD_TIMEOUT_MS = const(5000)  # 5 seconds

# Basic AT Commands
# ref: https://espressif-docs.readthedocs-hosted.com/projects/esp-at/en/release-v2.3.0.0_esp8266/AT_Command_Set/Basic_AT_Commands.html
_CMD_TEST = const(b"AT")
# WiFi AT Commands
# ref: https://espressif-docs.readthedocs-hosted.com/projects/esp-at/en/release-v2.3.0.0_esp8266/AT_Command_Set/Wi-Fi_AT_Commands.html
_CMD_WIFI_GET_MODE = const(b"AT+CWMODE?")
_CMD_WIFI_SET_MODE = const(b"AT+CWMODE=")
_CMD_WIFI_CONNECT_AP = const(b"AT+CWJAP=")
_CMD_WIFI_DISCONNECT_AP = const(b"AT+CWQAP")
# TCP/IP AT Commands
# ref: https://espressif-docs.readthedocs-hosted.com/projects/esp-at/en/release-v2.3.0.0_esp8266/AT_Command_Set/TCP-IP_AT_Commands.html
_CMD_TCP_GET_CONNECTION_MULTIPLEXING = const(b"AT+CIPMUX?")
_CMD_TCP_SET_CONNECTION_MULTIPLEXING = const(b"AT+CIPMUX=")
_CMD_TCP_START_SERVER = const(b"AT+CIPSERVER=")
_CMD_TCP_STOP_SERVER = const(b"AT+CIPSERVER=")
_CMD_TCP_SET_IPD_MESSAGE_MODE = const(b"AT+CIPDINFO=")
_CMD_TCP_SEND_DATA = const(b"AT+CIPSEND=")
_CMD_TCP_SEND_DATA_EX = const(b"AT+CIPSEND=")

_CMD_RESPONSE_OK = const(b"OK\r\n")
_CMD_RESPONSE_ERROR = const(b"ERROR\r\n")
_CMD_RESPONSE_FAIL = const(b"FAIL\r\n")

WIFI_MODE_OFF = const(0)
WIFI_MODE_STATION = const(1)
WIFI_MODE_ACCESS_POINT = const(2)
WIFI_MODE_BOTH = const(WIFI_MODE_STATION + WIFI_MODE_ACCESS_POINT)

SERVER_MULTIPLEXING_MODE_OFF = const(0)
SERVER_MULTIPLEXING_MODE_ON = const(1)


class ESP01S:
    __slots__ = (
        "_uart",
        "_cmd_lock",
        "_cmd_response_prefix",
        "_cmd_response_bytes",
        "_cmd_response_complete",
        "_tcp_server",
    )

    _uart: machine.UART

    _cmd_lock: uasyncio.Lock
    _cmd_response_prefix: bytes
    _cmd_response_bytes: bytes
    _cmd_response_complete: uasyncio.Event

    _tcp_server: _tcp.TCPServer

    def __init__(
        self,
        uart_id: int = _DEFAULT_UART_ID,
        tx_pin: int = _DEFAULT_UART_TX_PIN,
        rx_pin: int = _DEFAULT_UART_RX_PIN,
        on_tcp_connection_opened: Callable[[int], None] | None = None,
        on_tcp_connection_closed: Callable[[int], None] | None = None,
        on_tcp_connection_data: Callable[[int, memoryview], None] | None = None,
    ):
        self._uart = machine.UART(
            uart_id,
            tx=machine.Pin(tx_pin),
            rx=machine.Pin(rx_pin),
            txbuf=_DEFAULT_UART_TX_BUFFER_LEN,
            rxbuf=_DEFAULT_UART_RX_BUFFER_LEN,
            baudrate=_DEFAULT_UART_BAUD_RATE,
        )

        self._cmd_lock = uasyncio.Lock()
        self._cmd_response_complete = uasyncio.Event()

        self._tcp_server = _tcp.TCPServer(
            on_tcp_connection_opened,
            on_tcp_connection_closed,
            on_tcp_connection_data,
        )

        self._flush()

    def _flush(self):
        self._cmd_response_prefix = b""
        self._cmd_response_bytes = b""

    def _get_cmd_response_prefix(self, command: bytes) -> bytes:
        """
        Get expected response prefix from command.

        Examples:

        - AT+CWLAP -> +CWLAP
        - AT+CIFSR -> +CIFSR
        - AT -> AT

        Args:
            command (bytes): Command to determine the prefix from.

        Returns:
            bytes: Expected prefix for the given command.
        """
        if command == _CMD_TEST:
            # The AT command is a special child that does not follow any of the others,
            # it's response prefix is just AT
            return _CMD_TEST.rstrip(b"\r\n")

        end = 3  # ignore the AT+ prefix
        for i in range(3, len(command)):
            c = command[i]
            # keep reading until we find the end of the command name (denoted by ?, = or a line ending)
            if c in (61, 63, 13, 10):  # ord("="), ord("?"), ord("\r"), ord("\n")
                break
            end = i + 1

        return b"+" + command[3:end]

    def _escape_param(self, param: bytes):
        """
        Escape parameter for AT command if needed.

        Quotes and escapes params containing special characters (space,
        quote, comma, backslash). Pre-quoted params are normalized.

        Args:
            param (bytes): Raw parameter as bytes.

        Returns:
            Original param if clean, otherwise escaped and quoted bytes.
        """

        if b" " in param or b'"' in param or b"," in param or b"\\" in param:
            p = param.lstrip(b'"')
            p = p.replace(b"\\", b"\\\\", -1)
            p = p.replace(b'"', b'\\"', -1)
            p = p.replace(b",", b"\\,", -1)

            return b'"' + p + b'"'

        return param

    def _build_params(self, required: list[bytes], optional: list[bytes | None] | None = None):
        """
        Build comma-separated AT command parameter string.

        Escapes and joins required params, then any non-None optional params.

        Args:
            required: List of bytes params to include.
            optional: List of bytes or None; None values are skipped.

        Returns:
            Escaped params joined by commas, e.g. b'"param1","param2"'
        """

        parts = []
        append = parts.append
        escape = self._escape_param

        for p in required:
            append(escape(p))

        if optional:
            for p in optional:
                if p is not None:
                    append(escape(p))

        return b",".join(parts)

    async def _send_command(
        self,
        command: bytes,
        timeout_ms: int = _DEFAULT_CMD_TIMEOUT_MS,
    ):
        async with self._cmd_lock:
            self._cmd_response_prefix = self._get_cmd_response_prefix(command)
            self._cmd_response_bytes = b""
            self._cmd_response_complete.clear()

            self._uart.write(command + b"\r\n")

            await uasyncio.wait_for(
                self._cmd_response_complete.wait(), timeout_ms / 1000
            )

            response = self._cmd_response_bytes

            self._cmd_response_complete.clear()
            self._flush()

            return response

    async def receive(self) -> None:
        if self._uart.any():
            chunk = self._uart.read()
            if chunk:
                # Handle tcp server messages
                if self._tcp_server:
                    self._tcp_server.handle_message(chunk)

                # Handle responses if we sent a command
                if self._cmd_lock.locked:
                    has_prefix = self._cmd_response_prefix in chunk
                    has_ending = any(
                        prefix in chunk
                        for prefix in (
                            _CMD_RESPONSE_OK,
                            _CMD_RESPONSE_ERROR,
                            _CMD_RESPONSE_FAIL,
                        )
                    )

                    if has_prefix or has_ending:
                        self._cmd_response_bytes += chunk

                        if has_ending:
                            self._cmd_response_complete.set()

        await uasyncio.sleep(0.01)

    async def test(self) -> bool:
        """
        Sends a test command to the ESP01S. This is useful to verify we can talk to it using UART.

        Returns:
            bool: True if we get a successful response, False otherwise.
        """
        return _CMD_RESPONSE_OK in await self._send_command(_CMD_TEST)

    async def set_wifi_mode(self, mode=WIFI_MODE_BOTH) -> bool:
        """
        Sets the Wi-Fi Mode of the ESP01S.

        - WIFI_MODE_OFF -- turns off the ESP01S's radio
        - WIFI_MODE_STATION -- makes the ESP01S act as a WiFi client, only connecting to the access point
        - WIFI_MODE_ACCESS_POINT -- makes the ESP01S act as a WiFi network, allowing clients to connect to it like an access point
        - WIFI_MODE_BOTH -- does both modes above at the same time

        Returns:
            bool: True if the mode was set, False otherwise
        """

        response = await self._send_command(
            _CMD_WIFI_SET_MODE + self._build_params(required=[str(mode).encode()])
        )

        return _CMD_RESPONSE_OK in response

    async def connect_wifi_access_point(
        self, ssid: bytes, password: bytes, mac: bytes | None = None
    ) -> bool:
        """
        Asks the ESP01S to connect to the specified access point ssid.

        Returns:
            bool: True if we connected, False otherwise
        """
        response = await self._send_command(
            _CMD_WIFI_CONNECT_AP
            + self._build_params(
                required=[ssid, password],
                optional=[mac],
            ),
            timeout_ms=30000,  # 30 seconds
        )

        return _CMD_RESPONSE_OK in response

    async def disconnect_wifi_access_point(self) -> bool:
        """
        Asks the ESP01S to disconnect from the currently connected access point.

        Returns:
            bool: True if we disconnected, False otherwise
        """
        response = await self._send_command(_CMD_WIFI_DISCONNECT_AP)
        return _CMD_RESPONSE_OK in response

    async def set_tcp_ipd_message_mode(
        self,
        mode: int = 0,
    ) -> bool:
        """
        Configure the format of incoming +IPD data messages.

        Sends the AT+CIPDINFO=<mode> command to control whether the remote
        IP address and port are included in +IPD messages.

        Args:
            mode (int): The +IPD message format.
                - 0: Short format (default).
                    +IPD,<conn_id>,<len>:<data>
                - 1: Extended format with remote endpoint info.
                    +IPD,<conn_id>,<len>,<remote_ip>,<remote_port>:<data>

        Returns:
            bool: True if the mode was successfully set, False otherwise.
        """
        response = await self._send_command(
            _CMD_TCP_SET_IPD_MESSAGE_MODE
            + self._build_params(
                required=[str(mode).encode()],
            )
        )

        return _CMD_RESPONSE_OK in response

    async def set_tcp_server_connection_multiplexing(
        self, mode: int = SERVER_MULTIPLEXING_MODE_ON
    ) -> bool:
        """
        Configure the TCP connection multiplexing mode.

        Sends the AT+CIPMUX=<mode> command to enable or disable multiple
        simultaneous TCP connections. Multi-connection mode is recommended
        before starting a TCP server.

        Args:
            mode: The multiplexing mode to set.
                - SERVER_MULTIPLEXING_MODE_ON (1): Enable multiple connections.
                - SERVER_MULTIPLEXING_MODE_OFF (0): Single connection only.
                Defaults to SERVER_MULTIPLEXING_MODE_ON.

        Returns:
            bool: True if the mode was successfully set, False otherwise.
        """

        response = await self._send_command(
            _CMD_TCP_SET_CONNECTION_MULTIPLEXING
            + self._build_params(
                required=[str(mode).encode()],
            )
        )

        return _CMD_RESPONSE_OK in response

    async def start_tcp_server(self, port: int) -> bool:
        """
        Start a TCP server on the ESP-01S module.

        Sends the AT+CIPSERVER=1,<port> command to begin listening for
        incoming TCP connections on the specified port.

        Args:
            port: The TCP port number to listen on (e.g., 80 for HTTP).

        Returns:
            bool: True if the server was successfully started, False otherwise.
        """

        response = await self._send_command(
            _CMD_TCP_START_SERVER
            + self._build_params(
                required=[b"1", str(port).encode()],
            )
        )

        return _CMD_RESPONSE_OK in response

    async def stop_tcp_server(self) -> bool:
        """
        Stop the TCP server on the ESP-01S module.

        Sends the AT+CIPSERVER=0 command to close any active TCP server
        and stop listening for incoming connections.

        Returns:
            bool: True if the server was successfully stopped, False otherwise.
        """

        response = await self._send_command(
            _CMD_TCP_STOP_SERVER
            + self._build_params(
                required=[b"0"],
            )
        )

        return _CMD_RESPONSE_OK in response

    async def send_tcp_server_connection_data(
        self,
        connection_id: int,
        data: memoryview,
    ) -> None:
        pass
