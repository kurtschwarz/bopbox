from micropython import const

from bopbox.util import find_ord_in_memoryview

_ORD_SPACE = const(0x20)  # ord(" ")
_ORD_COLON = const(0x3A)  # ord(":")


class HTTPContext:
    __slots__ = (
        "connection_id",
        "request",
        "response",
    )

    connection_id: int
    request: HTTPRequest
    response: HTTPResponse

    def __init__(
        self,
        connection_id: int,
        request: HTTPRequest,
        response: HTTPResponse,
    ) -> None:
        self.connection_id = connection_id
        self.request = request
        self.response = response


class HTTPRequest:
    __slots__ = (
        "method",
        "path",
        "headers",
        "body",
    )

    method: bytes
    path: bytes
    headers: dict
    body: memoryview | None

    def __init__(
        self,
        method: bytes,
        path: bytes,
        headers: dict,
        body: memoryview | None = None,
    ) -> None:
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body

    @staticmethod
    def parse(
        data: memoryview,
    ) -> HTTPRequest | None:
        request = None

        reading_first_line = True
        reading_header_lines = False
        header_lines_end = 0

        line_start, view_offset = 0, 0
        while view_offset < len(data) - 1:
            if data[view_offset] == 0x0D and data[view_offset + 1] == 0x0A:
                line = data[line_start:view_offset]

                if reading_first_line:
                    # attempt to parse the first line of the message:
                    # GET /test HTTP/1.1

                    method_space = find_ord_in_memoryview(line, _ORD_SPACE)
                    path_space = method_space + find_ord_in_memoryview(
                        line[method_space + 1 :], _ORD_SPACE
                    )

                    if method_space != -1 and path_space != -1:
                        method = bytes(line[:method_space])
                        path = bytes(line[method_space + 1 : path_space + 1])

                        if method and path:
                            request = HTTPRequest(
                                method=method,
                                path=path,
                                headers={},
                            )

                    reading_first_line = False
                    reading_header_lines = True
                elif reading_header_lines:
                    if len(line) == 0:
                        reading_header_lines = False
                        header_lines_end = (
                            view_offset + 2
                        )  # add 2 to account for the /r/n ending

                        break

                    colon = find_ord_in_memoryview(line, _ORD_COLON)
                    if colon != -1 and request:
                        key = bytes(line[:colon]).strip().lower()
                        value = bytes(line[colon + 1 :]).strip()
                        request.headers[key] = value

                line_start = view_offset + 2
                view_offset += 1
            view_offset += 1

        if request:
            request.body = data[header_lines_end:]

        return request


class HTTPResponse:
    __slots__ = ""

    def __init__(self) -> None:
        pass
