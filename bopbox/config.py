import ujson


class Config:
    __slots__ = ("debug_mode", "wifi_ssid", "wifi_password")

    debug_mode: bool

    wifi_ssid: str | None
    wifi_password: str | None

    def __init__(self) -> None:
        self.debug_mode = False
        self.wifi_ssid = None
        self.wifi_password = None

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
