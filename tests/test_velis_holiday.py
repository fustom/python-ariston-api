"""Unit tests for the Velis holiday write (endpoint proven by live write-test)."""

import asyncio
import unittest
from datetime import date
from typing import Any
from unittest.mock import patch

from ariston.ariston_api import AristonAPI
from ariston.const import ARISTON_API_URL, ARISTON_VELIS
from ariston.velis_device import AristonVelisDevice

GW = "3C8A1F2EDE84"
EXPECTED_URL = (
    f"{ARISTON_API_URL}{ARISTON_VELIS}/slpPlantData/{GW}/holiday"
)


def _fake_session_cls(posts: list):
    class _Session:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_Session":
            return self

        async def __aexit__(self, *exc: Any) -> bool:
            return False

        async def request(self, method: str, path: str, params=None, json=None,
                          headers=None):
            if method == "POST":
                posts.append({"path": path, "json": json})
            class _Resp:
                status = 200
                ok = True
                content_length = 0
            return _Resp()

    return _Session


def _device() -> AristonVelisDevice:
    """Instantiate without the abstract machinery; only api+gw are used."""
    cls = AristonVelisDevice
    original = cls.__abstractmethods__
    cls.__abstractmethods__ = frozenset()
    try:
        device = cls.__new__(cls)
    finally:
        cls.__abstractmethods__ = original
    device.api = AristonAPI("user", "pass")
    device.gw = GW
    return device


class VelisHolidayTests(unittest.TestCase):
    """Device wrapper delegates to the API holiday pair with date formatting."""

    def test_holiday_end_date_format(self):
        self.assertEqual(
            AristonVelisDevice._create_holiday_end_date(date(2026, 9, 15)),
            "2026-09-15T00:00:00",
        )
        self.assertIsNone(AristonVelisDevice._create_holiday_end_date(None))

    def test_async_set_velis_holiday_on_posts_date(self):
        posts: list = []
        device = _device()
        with patch(
            "ariston.ariston_api.aiohttp.ClientSession", _fake_session_cls(posts)
        ):
            asyncio.run(device.async_set_velis_holiday(date(2026, 9, 15)))

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["path"], EXPECTED_URL)
        self.assertEqual(posts[0]["json"], {"new": "2026-09-15T00:00:00"})

    def test_async_set_velis_holiday_off_posts_null(self):
        posts: list = []
        device = _device()
        with patch(
            "ariston.ariston_api.aiohttp.ClientSession", _fake_session_cls(posts)
        ):
            asyncio.run(device.async_set_velis_holiday(None))

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["path"], EXPECTED_URL)
        self.assertEqual(posts[0]["json"], {"new": None})


if __name__ == "__main__":
    unittest.main()
