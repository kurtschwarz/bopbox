import machine
import uasyncio

from micropython import const


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

_CMD_RESPONSE_OK = const(b"OK\r\n")
_CMD_RESPONSE_ERROR = const(b"ERROR\r\n")
_CMD_RESPONSE_FAIL = const(b"FAIL\r\n")

WIFI_MODE_OFF = const(0)
WIFI_MODE_STATION = const(1)
WIFI_MODE_ACCESS_POINT = const(2)
WIFI_MODE_BOTH = const(WIFI_MODE_STATION + WIFI_MODE_ACCESS_POINT)


class ESP01S:
    __slots__ = (
        "_uart",
        "_cmd_lock",
        "_cmd_response_prefix",
        "_cmd_response_bytes",
        "_cmd_response_complete",
    )

    _uart: machine.UART

    _cmd_lock: uasyncio.Lock
    _cmd_response_prefix: bytes
    _cmd_response_bytes: bytes
    _cmd_response_complete: uasyncio.Event

    def __init__(
        self,
        uart_id: int = _DEFAULT_UART_ID,
        tx_pin: int = _DEFAULT_UART_TX_PIN,
        rx_pin: int = _DEFAULT_UART_RX_PIN,
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
            if c in (ord("="), ord("?"), ord("\r"), ord("\n")):
                break
            end = i + 1

        return b"+" + command[3:end]

    def _escape_param(self, input: bytes) -> bytes:
        if b" " in input or b'"' in input or b"," in input or b"\\" in input:
            return (
                b'"'
                + input.lstrip(b'"')
                .rstrip(b'"')
                .replace(b"\\", b"\\\\")
                .replace(b'"', b'\\"')
                .replace(b",", b"\\,")
                + b'"'
            )

        return input

    def _build_params(
        self, required: list[bytes], optional: list[bytes | None] = []
    ) -> bytes:
        return b",".join(
            map(
                self._escape_param,
                required + [param for param in optional if param is not None],
            )
        )

    async def _send_command(
        self, command: bytes, timeout_ms: int = _DEFAULT_CMD_TIMEOUT_MS
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

    async def poll(self) -> None:
        if self._uart.any():
            chunk = self._uart.read()
            if chunk:
                # @TODO add handling for network requests/responses

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
