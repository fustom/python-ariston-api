"""Unit tests for the Nuos Split GREEN write via the R2 web-app endpoint."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ariston.ariston_api import AristonAPI, ConnectionException
from ariston.const import NuosSplitOperativeMode
from ariston.nuos_split_device import AristonNuosSplitDevice


def _device() -> AristonNuosSplitDevice:
    """Instantiate without the abstract machinery; only api+gw are used."""
    cls = AristonNuosSplitDevice
    original = cls.__abstractmethods__
    cls.__abstractmethods__ = frozenset()
    try:
        device = cls.__new__(cls)
    finally:
        cls.__abstractmethods__ = original
    device.api = AristonAPI("user", "pass")
    device.gw = "3C8A1F2EDE84"
    device.data = {}
    return device


def test_build_nuos_r2_payload_green() -> None:
    plant = {
        "gw": "3C8A1F2EDE84",
        "on": True,
        "mode": 2,
        "waterTemp": 49.0,
        "comfortTemp": 54.0,
        "reducedTemp": 16.0,
        "procReqTemp": 54.0,
        "opMode": 1,
        "holidayUntil": None,
        "boostOn": False,
        "hpState": 2,
    }
    payload = AristonAPI._build_nuos_r2_payload(plant, NuosSplitOperativeMode.GREEN.value)

    assert payload["viewModel"]["opMode"] == 0  # GREEN — the value that must change
    assert payload["viewModel"]["plantMode"] == 2
    assert payload["viewModel"]["comfortTemp"] == 54.0
    assert payload["plantData"]["gatewayId"] == "3C8A1F2EDE84"
    assert payload["plantData"]["__type__"] == [
        "my.entities.entityiface",
        "my.entities.slpplantdata",
    ]


def test_green_write_routes_through_r2() -> None:
    device = _device()
    device.api.async_set_nuos_mode_via_r2 = AsyncMock()  # type: ignore[method-assign]
    device.api.async_set_nuos_mode = AsyncMock()  # type: ignore[method-assign]

    asyncio.run(device.async_set_water_heater_operation_mode("GREEN"))

    device.api.async_set_nuos_mode_via_r2.assert_awaited_once_with(
        device.gw, NuosSplitOperativeMode.GREEN
    )
    device.api.async_set_nuos_mode.assert_not_awaited()
    assert device.data["opMode"] == 0


def test_comfort_write_keeps_direct_route() -> None:
    device = _device()
    device.api.async_set_nuos_mode_via_r2 = AsyncMock()  # type: ignore[method-assign]
    device.api.async_set_nuos_mode = AsyncMock()  # type: ignore[method-assign]

    asyncio.run(device.async_set_water_heater_operation_mode("COMFORT"))

    device.api.async_set_nuos_mode.assert_awaited_once_with(
        device.gw, NuosSplitOperativeMode.COMFORT
    )
    device.api.async_set_nuos_mode_via_r2.assert_not_awaited()
    assert device.data["opMode"] == 1


def test_enum_values_match_official_range() -> None:
    assert NuosSplitOperativeMode.GREEN.value == 0
    assert NuosSplitOperativeMode.COMFORT.value == 1
    assert NuosSplitOperativeMode.FAST.value == 2
    assert NuosSplitOperativeMode.AUTO.value == 3  # was mislabeled IMEMORY


class _FakeAsyncCtx:
    """Minimal async context manager yielding a fake response."""

    def __init__(self, response: Any) -> None:
        self._response = response

    async def __aenter__(self) -> Any:
        return self._response

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _FakeSession:
    """Stand-in for aiohttp.ClientSession used as an async context manager."""

    def __init__(self, response: Any) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    def get(self, *args: Any, **kwargs: Any) -> _FakeAsyncCtx:
        return _FakeAsyncCtx(self._response)

    def post(self, *args: Any, **kwargs: Any) -> _FakeAsyncCtx:
        return _FakeAsyncCtx(self._response)


class _FakeResponse:
    def __init__(self, status: int, json_err: Exception | None = None) -> None:
        self.status = status
        self._json_err = json_err

    async def json(self) -> Any:
        if self._json_err is not None:
            raise self._json_err
        return {}


@pytest.mark.parametrize(
    "json_err",
    [
        KeyError("plantData"),
        ValueError("bad json"),
    ],
)
def test_r2_read_surfaces_connection_exception_on_bad_body(json_err: Exception) -> None:
    """Expired R2 session: GetData answers 200 with a non-plantData body.

    The read+parse must surface ConnectionException so the caller's
    fresh-login retry fires (regression guard for the silent-drop bug).
    """
    api = AristonAPI("user", "pass")
    fake = _FakeSession(_FakeResponse(200, json_err=json_err))
    with patch(
        "ariston.ariston_api.aiohttp.ClientSession", lambda *a, **kw: fake
    ):
        with pytest.raises(ConnectionException, match="session expired"):
            asyncio.run(api._async_r2_get_slp_plant_data("GW"))


def test_r2_retry_fires_fresh_login_after_failed_read() -> None:
    """One failed read -> fresh login -> retry read -> SetData POST."""
    api = AristonAPI("user", "pass")
    api._async_r2_login = AsyncMock()
    api._async_r2_get_slp_plant_data = AsyncMock(
        side_effect=[ConnectionException("expired"), {"any": "plant"}]
    )
    api._build_nuos_r2_payload = MagicMock(return_value={})
    fake = _FakeSession(_FakeResponse(200))
    with patch(
        "ariston.ariston_api.aiohttp.ClientSession", lambda *a, **kw: fake
    ):
        asyncio.run(
            api.async_set_nuos_mode_via_r2("GW", NuosSplitOperativeMode.GREEN)
        )
    assert api._async_r2_login.await_count == 2
    assert api._async_r2_get_slp_plant_data.await_count == 2
