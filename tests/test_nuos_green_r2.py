"""Unit tests for the Nuos Split GREEN write via the R2 web-app endpoint."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

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
    def __init__(
        self,
        status: int,
        json_err: Exception | None = None,
        json_data: Any = None,
    ) -> None:
        self.status = status
        self._json_err = json_err
        self._json_data = json_data

    async def json(self) -> Any:
        if self._json_err is not None:
            raise self._json_err
        return self._json_data if self._json_data is not None else {}


class _FakeRequestsSession:
    """Stand-in for requests.Session with queued responses."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self._responses: list[Any] = []
        self.posts: list[dict[str, Any]] = []

    def queue(self, *responses: Any) -> None:
        self._responses.extend(responses)

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return self._responses.pop(0)

    def post(self, *args: Any, **kwargs: Any) -> Any:
        self.posts.append(kwargs)
        return self._responses.pop(0)


class _FakeRequestsResponse:
    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        json_data: Any = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.ok = status_code < 400
        self._json_data = json_data

    def json(self) -> Any:
        return self._json_data if self._json_data is not None else {}


_LOGIN_HTML = '<input name="__RequestVerificationToken" value="TOKEN123" />'


class NuosGreenR2Tests(unittest.TestCase):
    """GREEN (0) must go through the R2 web-app route, sync and async."""

    def test_build_nuos_r2_payload_green(self) -> None:
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
        payload = AristonAPI._build_nuos_r2_payload(
            plant, NuosSplitOperativeMode.GREEN.value
        )

        self.assertEqual(payload["viewModel"]["opMode"], 0)  # the value that changes
        self.assertEqual(payload["viewModel"]["plantMode"], 2)
        self.assertEqual(payload["viewModel"]["comfortTemp"], 54.0)
        self.assertEqual(payload["plantData"]["gatewayId"], "3C8A1F2EDE84")
        self.assertEqual(
            payload["plantData"]["__type__"],
            ["my.entities.entityiface", "my.entities.slpplantdata"],
        )

    def test_enum_values_match_official_range(self) -> None:
        self.assertEqual(NuosSplitOperativeMode.GREEN.value, 0)
        self.assertEqual(NuosSplitOperativeMode.COMFORT.value, 1)
        self.assertEqual(NuosSplitOperativeMode.FAST.value, 2)
        self.assertEqual(NuosSplitOperativeMode.AUTO.value, 3)  # was mislabeled

    def test_imemory_alias_preserved(self) -> None:
        """IMEMORY (the pre-rename public name) still resolves to AUTO = 3."""
        self.assertIs(NuosSplitOperativeMode.IMEMORY, NuosSplitOperativeMode.AUTO)
        self.assertEqual(NuosSplitOperativeMode["IMEMORY"].value, 3)
        values = [mode.value for mode in NuosSplitOperativeMode]
        self.assertEqual(values.count(3), 1)  # alias adds no duplicate option
        self.assertNotIn("IMEMORY", [mode.name for mode in NuosSplitOperativeMode])

    def test_imemory_string_still_sets_auto(self) -> None:
        """The string-based setter accepts the old name and writes value 3."""
        device = _device()
        device.api.set_nuos_mode = MagicMock()

        device.set_water_heater_operation_mode("IMEMORY")

        device.api.set_nuos_mode.assert_called_once_with(
            device.gw, NuosSplitOperativeMode.AUTO
        )
        self.assertEqual(device.data["opMode"], 3)

    # -- async device setter routing --

    def test_green_write_routes_through_r2(self) -> None:
        device = _device()
        device.api.async_set_nuos_mode_via_r2 = AsyncMock()  # type: ignore[method-assign]
        device.api.async_set_nuos_mode = AsyncMock()  # type: ignore[method-assign]

        asyncio.run(device.async_set_water_heater_operation_mode("GREEN"))

        device.api.async_set_nuos_mode_via_r2.assert_awaited_once_with(
            device.gw, NuosSplitOperativeMode.GREEN
        )
        device.api.async_set_nuos_mode.assert_not_awaited()
        self.assertEqual(device.data["opMode"], 0)

    def test_comfort_write_keeps_direct_route(self) -> None:
        device = _device()
        device.api.async_set_nuos_mode_via_r2 = AsyncMock()  # type: ignore[method-assign]
        device.api.async_set_nuos_mode = AsyncMock()  # type: ignore[method-assign]

        asyncio.run(device.async_set_water_heater_operation_mode("COMFORT"))

        device.api.async_set_nuos_mode.assert_awaited_once_with(
            device.gw, NuosSplitOperativeMode.COMFORT
        )
        device.api.async_set_nuos_mode_via_r2.assert_not_awaited()
        self.assertEqual(device.data["opMode"], 1)

    # -- async API R2 flow --

    def test_r2_read_surfaces_connection_exception_on_bad_body(self) -> None:
        """Expired R2 session: GetData answers 200 with a non-plantData body.

        The read+parse must surface ConnectionException so the caller's
        fresh-login retry fires (regression guard for the silent-drop bug).
        """
        for json_err in (KeyError("plantData"), ValueError("bad json")):
            with self.subTest(json_err=type(json_err).__name__):
                api = AristonAPI("user", "pass")
                fake = _FakeSession(_FakeResponse(200, json_err=json_err))
                with patch(
                    "ariston.ariston_api.aiohttp.ClientSession", lambda *a, **kw: fake
                ):
                    with self.assertRaisesRegex(
                        ConnectionException, "session expired"
                    ):
                        asyncio.run(api._async_r2_get_slp_plant_data("GW"))

    def test_r2_retry_fires_fresh_login_after_failed_read(self) -> None:
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
        self.assertEqual(api._async_r2_login.await_count, 2)
        self.assertEqual(api._async_r2_get_slp_plant_data.await_count, 2)

    def test_r2_setdata_success_false_raises(self) -> None:
        """A 200 body with success:false is a failed write, not a success."""
        api = AristonAPI("user", "pass")
        api._async_r2_login = AsyncMock()
        api._async_r2_get_slp_plant_data = AsyncMock(return_value={"any": "plant"})
        fake = _FakeSession(_FakeResponse(200, json_data={"success": False}))
        with patch(
            "ariston.ariston_api.aiohttp.ClientSession", lambda *a, **kw: fake
        ):
            with self.assertRaisesRegex(ConnectionException, "reported failure"):
                asyncio.run(
                    api.async_set_nuos_mode_via_r2("GW", NuosSplitOperativeMode.GREEN)
                )

    def test_r2_setdata_non_json_body_raises(self) -> None:
        """An expired session turns the POST into a 200 login page."""
        api = AristonAPI("user", "pass")
        api._async_r2_login = AsyncMock()
        api._async_r2_get_slp_plant_data = AsyncMock(return_value={"any": "plant"})
        err = aiohttp.ContentTypeError(MagicMock(), ())
        fake = _FakeSession(_FakeResponse(200, json_err=err))
        with patch(
            "ariston.ariston_api.aiohttp.ClientSession", lambda *a, **kw: fake
        ):
            with self.assertRaisesRegex(ConnectionException, "non-JSON body"):
                asyncio.run(
                    api.async_set_nuos_mode_via_r2("GW", NuosSplitOperativeMode.GREEN)
                )

    # -- sync twin (requests) --

    def test_sync_green_write_full_r2_flow(self) -> None:
        """Sync GREEN: login -> read -> write, opMode 0 in the SetData envelope."""
        api = AristonAPI("user", "pass")
        session = _FakeRequestsSession()
        session.queue(
            _FakeRequestsResponse(200, text=_LOGIN_HTML),
            _FakeRequestsResponse(302),
            _FakeRequestsResponse(
                json_data={"data": {"plantData": {"mode": 2, "on": True}}}
            ),
            _FakeRequestsResponse(json_data={"success": True}),
        )
        with patch("ariston.ariston_api.requests.Session", lambda: session):
            api.set_nuos_mode_via_r2("GW", NuosSplitOperativeMode.GREEN)

        self.assertEqual(len(session.posts), 2)
        login_form = session.posts[0]["data"]
        self.assertEqual(login_form["__RequestVerificationToken"], "TOKEN123")
        setdata_body = session.posts[1]["json"]
        self.assertEqual(setdata_body["viewModel"]["opMode"], 0)
        self.assertEqual(setdata_body["plantData"]["mode"], 2)  # echoed back

    def test_sync_r2_retry_fires_fresh_login(self) -> None:
        """Sync twin of the async retry: one failed read -> fresh login -> retry."""
        api = AristonAPI("user", "pass")
        api._r2_login = MagicMock()
        api._r2_get_slp_plant_data = MagicMock(
            side_effect=[ConnectionException("expired"), {"any": "plant"}]
        )
        session = _FakeRequestsSession()
        session.queue(_FakeRequestsResponse(json_data={"success": True}))
        with patch("ariston.ariston_api.requests.Session", lambda: session):
            api.set_nuos_mode_via_r2("GW", NuosSplitOperativeMode.GREEN)

        self.assertEqual(api._r2_login.call_count, 2)
        self.assertEqual(api._r2_get_slp_plant_data.call_count, 2)

    def test_sync_green_write_routes_through_r2(self) -> None:
        """Device sync setter: GREEN must not hit the api/v2 direct route."""
        device = _device()
        device.api.set_nuos_mode_via_r2 = MagicMock()
        device.api.set_nuos_mode = MagicMock()

        device.set_water_heater_operation_mode("GREEN")

        device.api.set_nuos_mode_via_r2.assert_called_once_with(
            device.gw, NuosSplitOperativeMode.GREEN
        )
        device.api.set_nuos_mode.assert_not_called()
        self.assertEqual(device.data["opMode"], 0)

    def test_sync_comfort_write_keeps_direct_route(self) -> None:
        """Device sync setter: COMFORT keeps the proven api/v2 direct route."""
        device = _device()
        device.api.set_nuos_mode_via_r2 = MagicMock()
        device.api.set_nuos_mode = MagicMock()

        device.set_water_heater_operation_mode("COMFORT")

        device.api.set_nuos_mode.assert_called_once_with(
            device.gw, NuosSplitOperativeMode.COMFORT
        )
        device.api.set_nuos_mode_via_r2.assert_not_called()
        self.assertEqual(device.data["opMode"], 1)


if __name__ == "__main__":
    unittest.main()
