import ujson


class Config:
    __slots__ = (
        "debug_mode",
        "wifi_ssid",
        "wifi_password",
        "http_server_enabled",
        "http_server_port",
        "nfc_enabled",
    )

    debug_mode: bool

    wifi_ssid: str | None
    wifi_password: str | None

    http_server_enabled: bool | None
    http_server_port: int | None

    nfc_enabled: bool | None

    def __init__(self) -> None:
        self.debug_mode = False

        self.wifi_ssid = None
        self.wifi_password = None

        self.http_server_enabled = False
        self.http_server_port = None

        self.nfc_enabled = False

        self.load()

    def load(self) -> None:
        try:
            with open("./config.json", "r") as f:
                data = ujson.load(f)

            for key, value in data.items():
                if key in self.__slots__:
                    setattr(self, key, value)
        except OSError:
            pass


config = Config()
