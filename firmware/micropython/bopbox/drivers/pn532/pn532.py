import utime
import uasyncio
import machine

from typing import Callable
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
_CMD_IN_LIST_PASSIVE_TARGET = const(0x4A)

# ref: https://www.nxp.com/docs/en/user-guide/141520.pdf (§6.2.1.1)
_FRAME_PART_PREAMBLE = const(0x00)
_FRAME_PART_START_CODE1 = const(0x00)
_FRAME_PART_START_CODE2 = const(0xFF)
_FRAME_PART_POSTAMBLE = const(0x00)
_FRAME_PART_HOST_TO_PN532 = const(0xD4)
_FRAME_PART_PN532_TO_HOST = const(0xD5)

_FRAME_WAKE_UP = const(b"\x55\x55\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

_FRAME_TYPE_ACK = const(0)
_FRAME_TYPE_NACK = const(1)
_FRAME_TYPE_DATA = const(2)

_FRAME_PARSER_STATE_IDLE = const(0)
_FRAME_PARSER_STATE_PARSE_START1 = const(1)
_FRAME_PARSER_STATE_PARSE_LEN = const(2)
_FRAME_PARSER_STATE_PARSE_LCS = const(3)
_FRAME_PARSER_STATE_PARSE_BODY = const(4)
_FRAME_PARSER_STATE_PARSE_DCS = const(5)
_FRAME_PARSER_STATE_PARSE_POSTAMBLE = const(6)


class PN532Frame:
    __slots__ = (
        "type",
        "command",
        "data",
    )

    type: int
    command: int | None
    data: bytearray | None

    def __init__(
        self,
        type: int,
        command: int | None = None,
        data: bytearray | None = None,
    ) -> None:
        self.type = type
        self.command = command
        self.data = data


class PN532FrameParser:
    __slots__ = (
        "_state",
        "_buffer",
        "_pos",
        "_len",
        "_lcs",
        "_on_error",
        "_on_frame",
    )

    _state: int

    _buf: bytearray
    _pos: int
    _len: int
    _lcs: int

    _on_error: Callable[[PN532Error], None]
    _on_frame: Callable[[PN532Frame], None]

    def __init__(
        self,
        on_error: Callable[[PN532Error], None],
        on_frame: Callable[[PN532Frame], None],
    ) -> None:
        self._state = _FRAME_PARSER_STATE_IDLE
        self._buffer = bytearray(_DEFAULT_UART_RX_BUFFER_LEN)
        self._pos = 0
        self._len = 0
        self._lcs = 0
        self._on_error = on_error
        self._on_frame = on_frame

    def reset(self) -> None:
        self._state = _FRAME_PARSER_STATE_IDLE
        self._pos = 0
        self._len = 0
        self._lcs = 0

    def _signal_error(self, error: PN532Error) -> None:
        self._on_error(error)
        self.reset()

    def _signal_frame(self, frame: PN532Frame) -> None:
        self._on_frame(frame)

    def process(self, data: bytes) -> None:
        buffer = self._buffer

        for i in range(len(data)):
            byte = data[i]
            state = self._state

            if state == _FRAME_PARSER_STATE_IDLE:
                if byte == _FRAME_PART_START_CODE1:
                    self._state = _FRAME_PARSER_STATE_PARSE_START1

            elif state == _FRAME_PARSER_STATE_PARSE_START1:
                if byte == _FRAME_PART_START_CODE2:
                    self._state = _FRAME_PARSER_STATE_PARSE_LEN
                elif byte != _FRAME_PART_START_CODE1:
                    self._state = _FRAME_PARSER_STATE_IDLE

            elif state == _FRAME_PARSER_STATE_PARSE_LEN:
                self._len = byte
                self._state = _FRAME_PARSER_STATE_PARSE_LCS

            elif state == _FRAME_PARSER_STATE_PARSE_LCS:
                self._lcs = byte

                ln = self._len
                lcs = self._lcs

                if ln == 0x00 and lcs == 0xFF:
                    self._len = 0
                    self._state = _FRAME_PARSER_STATE_PARSE_POSTAMBLE
                elif ln == 0xFF and lcs == 0x00:
                    self._state = _FRAME_PARSER_STATE_PARSE_POSTAMBLE
                elif (ln + lcs) & 0xFF != 0:
                    self._signal_error(PN532Error(f"Bad LCS: {lcs}"))
                elif ln < 1:
                    self._signal_error(PN532Error("Empty Frame"))
                elif ln > len(self._buffer):
                    self._signal_error(PN532Error(f"Frame too large: {ln}"))
                else:
                    self._pos = 0
                    self._state = _FRAME_PARSER_STATE_PARSE_BODY

            elif state == _FRAME_PARSER_STATE_PARSE_BODY:
                buffer[self._pos] = byte
                self._pos += 1
                if self._pos >= self._len:
                    self._state = _FRAME_PARSER_STATE_PARSE_DCS

            elif state == _FRAME_PARSER_STATE_PARSE_DCS:
                dcs_sum = byte
                for j in range(self._len):
                    dcs_sum += buffer[j]

                if dcs_sum & 0xFF != 0:
                    self._signal_error(PN532Error(f"Bad DCS: {dcs_sum}"))
                else:
                    self._state = _FRAME_PARSER_STATE_PARSE_POSTAMBLE

            elif state == _FRAME_PARSER_STATE_PARSE_POSTAMBLE:
                ln = self._len
                if ln == 0:
                    self._signal_frame(PN532Frame(_FRAME_TYPE_ACK))
                elif ln == 0xFF:
                    self._signal_frame(PN532Frame(_FRAME_TYPE_NACK))
                elif buffer[0] != _FRAME_PART_PN532_TO_HOST:
                    self._signal_error(PN532Error(f"Bad TFI: {buffer[0]}"))
                else:
                  self._signal_frame(
                      PN532Frame(_FRAME_TYPE_DATA, buffer[1], buffer[2:ln])
                  )

                self._state = _FRAME_PARSER_STATE_IDLE


class PN532Error(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class PN532:
    __slots__ = (
        "_logger",
        "_uart",
        "_send_command_lock",
        "_frame_parser",
        "_frame_ready",
        "_frame_queue",
    )

    _logger: logger.Logger
    _uart: machine.UART

    _send_command_lock: uasyncio.Lock

    _frame_parser: PN532FrameParser
    _frame_ready: uasyncio.Event
    _frame_queue: list[PN532Frame]

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

        self._frame_parser = PN532FrameParser(
            on_error=self._handle_frame_parser_error,
            on_frame=self._handle_frame_parser_result,
        )

        self._frame_ready = uasyncio.Event()
        self._frame_queue = []

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
    ) -> PN532Frame:
        async with self._send_command_lock:
            await self.wake_up()

            # build and send the command frame
            command_frame = self._build_command_frame(command, data)
            await self._write_bytes(command_frame)

            # wait for the ACK frame
            await self._wait_frame(_FRAME_TYPE_ACK)

            # wait and return data frame
            return await self._wait_frame(_FRAME_TYPE_DATA)

    # --- UART Writing -----------------------------------------

    async def _write_bytes(self, data: bytes | bytearray) -> None:
        """Write data to UART, raising on failure."""
        written = self._uart.write(data)
        if written is None or written < len(data):
            raise PN532Error("UART write failed: %s/%d bytes" % (written, len(data)))

    # --- UART Reading -----------------------------------------

    def _handle_frame_parser_error(self, error: PN532Error) -> None:
        self._frame_ready.clear()

    def _handle_frame_parser_result(self, frame: PN532Frame) -> None:
        self._frame_ready.set()
        self._frame_queue.append(frame)

    async def receive(self) -> None:
        """Read data from UART"""
        if self._uart.any():
            data = self._uart.read()
            if data:
                self._frame_parser.process(data)

    #

    async def _wait_frame(
        self,
        expected_type=None,
        timeout_ms=_DEFAULT_CMD_TIMEOUT_MS,
    ):
        deadline = utime.ticks_add(utime.ticks_ms(), timeout_ms)

        while True:
            if self._frame_queue:
                frame = self._frame_queue.pop(0)
                if expected_type is None or frame.type == expected_type:
                    return frame

                continue

            remaining = utime.ticks_diff(deadline, utime.ticks_ms())
            if remaining <= 0:
                raise PN532Error("timeout")

            self._frame_ready.clear()

            try:
                await uasyncio.wait_for(
                    self._frame_ready.wait(),
                    remaining,
                )
            except uasyncio.TimeoutError:
                raise PN532Error("timeout")

    # --- High-Level Commands ----------------------------------

    async def wake_up(self) -> None:
        """Wake PN532 from low-power state on HSU interface."""
        await self._write_bytes(_FRAME_WAKE_UP)

    async def get_firmware_version(self) -> tuple:
        frame = await self._send_command(_CMD_GET_FIRMWARE_VERSION)
        return (frame.data[0], frame.data[1], frame.data[2], frame.data[3])

    async def get_passive_target(self) -> bytes | None:
        frame = await self._send_command(_CMD_IN_LIST_PASSIVE_TARGET, [0x01, 0x00])
        if frame.data is None or frame.data[0] == 0x00:
            return None

        return bytes(frame.data[6:6 + frame.data[5]])

    async def sam_config(self, mode=0x01):
        await self._send_command(0x14, [mode, 0x14, 0x01])

    async def set_retries(self, atr=0xFF, psl=0x01, passive=0x14):
        """
        Configure PN532 retry limits via RFConfiguration.

        Args:
            atr: Max ATR retries (0xFF = infinite)
            psl: Max PSL retries
            passive: Max passive activation retries.
                    Each retry is ~50ms. 0x14 (20) ≈ 1 second.
                    0xFF = wait forever.
        """
        await self._send_command(0x32, data=[0x05, atr, psl, passive])
