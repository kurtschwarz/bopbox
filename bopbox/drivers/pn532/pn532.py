import utime
import uasyncio
import machine

from micropython import const

from ...services import logger


_DEFAULT_UART_ID = const(0)
_DEFAULT_UART_TX_PIN = const(18)
_DEFAULT_UART_RX_PIN = const(19)
_DEFAULT_UART_BAUD_RATE = const(115200)
_DEFAULT_UART_TX_BUFFER_LEN = const(64)
_DEFAULT_UART_RX_BUFFER_LEN = const(_DEFAULT_UART_TX_BUFFER_LEN * 5)

_DEFAULT_CMD_TIMEOUT_MS = const(5000)  # 5 seconds

# ref: https://www.nxp.com/docs/en/user-guide/141520.pdf (§7)
_CMD_GET_FIRMWARE_VERSION = const(0x02)

# ref: https://www.nxp.com/docs/en/user-guide/141520.pdf (§6.2.1.1)
_FRAME_PART_PREAMBLE = const(0x00)
_FRAME_PART_START_CODE1 = const(0x00)
_FRAME_PART_START_CODE2 = const(0xFF)
_FRAME_PART_POSTAMBLE = const(0x00)
_FRAME_PART_HOST_TO_PN532 = const(0xD4)
_FRAME_PART_PN532_TO_HOST = const(0xD5)

_FRAME_WAKE_UP = const(b"\x55\x55\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")


class PN532Error(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class PN532:
    __slots__ = (
        "_logger",
        "_uart",
        "_send_command_lock",
    )

    _logger: logger.Logger
    _uart: machine.UART

    _send_command_lock: uasyncio.Lock

    def __init__(
        self,
        uart_id: int = _DEFAULT_UART_ID,
        tx_pin: int = _DEFAULT_UART_TX_PIN,
        rx_pin: int = _DEFAULT_UART_RX_PIN,
    ):
        self._logger = logger.get_logger("pn532")

        self._uart = machine.UART(
            uart_id,
            tx=machine.Pin(tx_pin),
            rx=machine.Pin(rx_pin),
            txbuf=_DEFAULT_UART_TX_BUFFER_LEN,
            rxbuf=_DEFAULT_UART_RX_BUFFER_LEN,
            baudrate=_DEFAULT_UART_BAUD_RATE,
        )

        self._send_command_lock = uasyncio.Lock()

    # ── Command Building & Sending ────────────────────────────

    def _build_command_frame(
        self,
        command: int,
        data: list[int] = [],
    ) -> bytearray:
        length = len(data) + 2
        lcs = (~length + 1) & 0xFF

        frame = bytearray(7 + len(data) + 2)
        frame[0] = 0x00
        frame[1] = _FRAME_PART_START_CODE1
        frame[2] = _FRAME_PART_START_CODE2
        frame[3] = length
        frame[4] = lcs
        frame[5] = _FRAME_PART_HOST_TO_PN532
        frame[6] = command

        dcs_sum = _FRAME_PART_HOST_TO_PN532 + command
        for i in range(len(data)):
            frame[7 + i] = data[i]
            dcs_sum += data[i]

        frame[-2] = (~dcs_sum + 1) & 0xFF
        frame[-1] = 0x00

        return frame

    async def _send_command(
        self,
        command: int,
        data: list[int] = [],
    ):
        self._logger.debug(f"_send_command called with command={command}")

        async with self._send_command_lock:
            # build and send the command frame
            command_frame = self._build_command_frame(command, data)
            await self._write_bytes(command_frame)

    # --- UART Writing -----------------------------------------

    async def _write_bytes(self, data: bytes | bytearray) -> None:
        """Write data to UART, raising on failure."""
        written = self._uart.write(data)
        if written is None or written < len(data):
            raise PN532Error("UART write failed: %s/%d bytes" % (written, len(data)))

    # --- UART Reading -----------------------------------------

    async def receive(self) -> None:
        """Read data from UART"""
        if self._uart.any():
            data = self._uart.read()
            if data:
                self._logger.debug(f"received data={data}")

        await uasyncio.sleep_ms(100)

    # --- High-Level Commands ----------------------------------

    async def wake_up(self) -> None:
        """Wake PN532 from low-power state on HSU interface."""
        await self._write_bytes(_FRAME_WAKE_UP)
        await uasyncio.sleep_ms(100)

    async def get_firmware_version(self) -> None:
        await self._send_command(_CMD_GET_FIRMWARE_VERSION)
