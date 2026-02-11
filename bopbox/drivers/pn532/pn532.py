import utime
import uasyncio
import machine

from micropython import const

from ...services import logger


_DEFAULT_UART_ID = const(0)
_DEFAULT_UART_TX_PIN = const(18)
_DEFAULT_UART_RX_PIN = const(19)
_DEFAULT_UART_BAUD_RATE = const(115200)
_DEFAULT_UART_TX_BUFFER_LEN = const(1024)
_DEFAULT_UART_RX_BUFFER_LEN = const(_DEFAULT_UART_TX_BUFFER_LEN * 2)


class PN532Error(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class PN532:
    __slots__ = (
        "_logger",
        "_uart",
    )

    _logger: logger.Logger

    _uart: machine.UART

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

    async def receive(self) -> None:
        if self._uart.any():
            data = self._uart.read()
            if data != None and len(data) > 0:
                self._logger.debug(f"received data={data}")

        await uasyncio.sleep_ms(100)
