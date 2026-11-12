"""Unit tests for the Velis holiday write (endpoint proven by live write-test)."""

import asyncio
from datetime import date
from typing import Any

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


def test_holiday_end_date_format():
    assert (
        AristonVelisDevice._create_holiday_end_date(date(2026, 9, 15))
        == "2026-09-15T00:00:00"
    )
    assert AristonVelisDevice._create_holiday_end_date(None) is None


def test_async_set_velis_holiday_on_posts_date():
    posts: list = []
    device = _device()
    with patch_session(_fake_session_cls(posts)):
        asyncio.run(device.async_set_velis_holiday(date(2026, 9, 15)))

    assert len(posts) == 1
    assert posts[0]["path"] == EXPECTED_URL
    assert posts[0]["json"] == {"new": "2026-09-15T00:00:00"}


def test_async_set_velis_holiday_off_posts_null():
    posts: list = []
    device = _device()
    with patch_session(_fake_session_cls(posts)):
        asyncio.run(device.async_set_velis_holiday(None))

    assert len(posts) == 1
    assert posts[0]["path"] == EXPECTED_URL
    assert posts[0]["json"] == {"new": None}


def patch_session(fake_cls):
    """Patch aiohttp.ClientSession inside ariston_api for one test."""
    from unittest.mock import patch

    return patch("ariston.ariston_api.aiohttp.ClientSession", fake_cls)
