import uasyncio

from typing import Callable
from micropython import const


_ORD_PLUS = const(0x2B)  # ord("+")
_ORD_0 = const(0x30)  # ord("0")

_MSG_URC_CONNECT = const(b",CONNECT\r\n")
_MSG_URC_CLOSED = const(b",CLOSED\r\n")
_MSG_URC_IPD = const(b"+IPD,")


class TCPServer:
    __slots__ = (
        "_requests",
        "_connections",
        "_on_connection_opened",
        "_on_connection_closed",
        "_on_connection_data",
    )

    _requests: list[uasyncio.Task]
    _connections: TCPServerConnections

    _on_connection_opened: Callable[[int], None] | None
    _on_connection_closed: Callable[[int], None] | None
    _on_connection_data: Callable[[int, memoryview], None] | None

    def __init__(
        self,
        on_connection_opened: Callable[[int], None] | None,
        on_connection_closed: Callable[[int], None] | None,
        on_connection_data: Callable[[int, memoryview], None] | None,
    ) -> None:
        self._connections = TCPServerConnections()

        self._on_connection_opened = on_connection_opened
        self._on_connection_closed = on_connection_closed
        self._on_connection_data = on_connection_data

    def _extract_connection_id(
        self,
        message: bytes,
    ) -> int:
        """
        Extract the connection ID from a URC message.

        Handles formats:
            - CONNECT/CLOSED: b"0,CONNECT", b"1,CLOSED"
            - IPD: b"+IPD,0,5:hello"

        Args:
            message: The raw URC message bytes.

        Returns:
            int: The connection ID (0-4).
        """

        # +IPD,<id>,<len>:<data>
        if message[0] == _ORD_PLUS:
            return message[5] - _ORD_0

        # <id>,CONNECT or <id>,CLOSED
        return message[0] - _ORD_0

    def handle_message(
        self,
        message: bytes,
    ) -> None:
        if _MSG_URC_CONNECT in message:
            connection_id = self._extract_connection_id(message)
            if connection_id in self._connections:
                return

            self._connections.add(connection_id)

        if _MSG_URC_CLOSED in message:
            connection_id = self._extract_connection_id(message)
            if connection_id not in self._connections:
                return

            self._connections.remove(connection_id)

        if _MSG_URC_IPD in message:
            connection_id = self._extract_connection_id(message)
            if connection_id not in self._connections:
                return

            if self._on_connection_data:
                data = memoryview(message)[
                    (message.find(b":", message.find(_MSG_URC_IPD)) + 1) :
                ]

                if len(data):
                    self._on_connection_data(
                        connection_id,
                        data,
                    )


class TCPServerConnections:
    """
    Memory-efficient tracker for active TCP server connections.

    Uses a bitmask to track connection IDs instead of a set or list,
    minimizing memory overhead on constrained microcontroller environments.

    The ESP-01S supports up to 5 simultaneous connections (IDs 0-4) in
    multi-connection mode.

    Example:
        connections = TCPServerConnections()
        connections.add(2)
        connections.add(4)

        if 2 in connections:
            print("Connection 2 is active")

        for conn_id in connections:
            print(f"Active: {conn_id}")  # Prints 2, 4
    """

    __slots__ = "_mask"

    _mask: int

    def __init__(self) -> None:
        self._mask = 0

    def add(self, connection_id: int) -> None:
        self._mask |= 1 << connection_id

    def remove(self, connection_id: int) -> None:
        self._mask &= ~(1 << connection_id)

    def __contains__(self, connection_id: int) -> bool:
        return bool(self._mask & (1 << connection_id))

    def __iter__(self):
        mask = self._mask
        connection_id = 0
        while mask:
            if mask & 1:
                yield connection_id
            mask >>= 1
            connection_id += 1
