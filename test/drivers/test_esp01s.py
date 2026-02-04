import sys
import pytest
import asyncio

from unittest.mock import MagicMock

sys.modules["uasyncio"] = asyncio
sys.modules["machine"] = MagicMock()
sys.modules["micropython"] = MagicMock()
sys.modules["micropython"].const = lambda x: x

from bopbox.drivers.esp01s import ESP01S


@pytest.fixture
def esp01s():
    return ESP01S()


class TestEP01SEscapeParams:

    def test_plain_string_unchanged(self, esp01s: ESP01S):
        assert esp01s._escape_param(b"hello") == b"hello"

    def test_escapes_backslash(self, esp01s: ESP01S):
        assert esp01s._escape_param(b"pass\\word") == b'"pass\\\\word"'

    def test_escapes_quote(self, esp01s: ESP01S):
        assert esp01s._escape_param(b'say "hi"') == b'"say \\"hi\\""'

    def test_escapes_comma(self, esp01s: ESP01S):
        assert esp01s._escape_param(b"a,b,c") == b'"a\\,b\\,c"'

    def test_escapes_combined(self, esp01s: ESP01S):
        assert (
            esp01s._escape_param(b'My "WiFi", Home\\Net')
            == b'"My \\"WiFi\\"\\, Home\\\\Net"'
        )
