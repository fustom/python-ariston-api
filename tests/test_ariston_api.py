"""Tests for authenticated cloud API requests."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import aiohttp

from ariston.ariston_api import AristonAPI, ConnectionException
from ariston.const import (
    BsbOperativeMode,
    BsbZoneMode,
    DeviceFeatures,
    EvoPlantMode,
    LydosPlantMode,
    NuosSplitOperativeMode,
    PlantData,
    ZoneAttribute,
)


class FakeResponse:
    def __init__(self, payload=None, status_code=200, content=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self._payload = payload
        self.content = content if content is not None else (
            b"response" if payload is not None else b""
        )

    def json(self):
        return self._payload


class FakeAsyncResponse(FakeResponse):
    def __init__(self, payload=None, status_code=200, content=None):
        super().__init__(payload, status_code, content)
        self.status = status_code
        self.content_length = len(self.content)

    async def json(self):
        return self._payload


class FakeAsyncSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


class FakeAsyncContent:
    def __init__(self, payload):
        self.payload = payload

    async def read(self):
        return self.payload


class FakeAsyncRateLimitedResponse(FakeAsyncResponse):
    def __init__(self):
        super().__init__(status_code=429, content=b"rate limited")
        self.content = FakeAsyncContent(b"rate limited")


class AristonAPIRequestTests(unittest.TestCase):
    def test_login_token_is_sent_with_followup_request(self):
        api = AristonAPI(
            "user@example.com",
            "password",
            api_url="https://example.test/api/",
            user_agent="test-agent",
        )
        responses = [
            FakeResponse({"token": "session-token"}),
            FakeResponse([{"gw": "gateway-1"}]),
        ]

        with patch(
            "ariston.ariston_api.requests.request", side_effect=responses
        ) as request:
            self.assertTrue(api.connect())
            devices = api.get_detailed_devices()

        self.assertEqual(devices, [{"gw": "gateway-1"}])
        login_call, devices_call = request.call_args_list
        # requests expects seconds: a regression to milliseconds (30000) would
        # let a hung connection block the caller for hours.
        self.assertEqual(login_call.kwargs["timeout"], 30)
        self.assertEqual(devices_call.kwargs["timeout"], 30)
        self.assertEqual(login_call.args[0], "POST")
        self.assertEqual(
            login_call.kwargs["json"],
            {"usr": "user@example.com", "pwd": "password"},
        )
        self.assertEqual(login_call.kwargs["headers"]["User-Agent"], "test-agent")
        self.assertEqual(login_call.kwargs["headers"]["ar.authToken"], "")
        self.assertEqual(devices_call.args[0], "GET")
        self.assertEqual(
            devices_call.args[1], "https://example.test/api/remote/plants"
        )
        self.assertEqual(devices_call.kwargs["headers"]["ar.authToken"], "session-token")

    def test_async_login_token_is_sent_with_followup_request(self):
        api = AristonAPI(
            "user@example.com",
            "password",
            api_url="https://example.test/api/",
            user_agent="test-agent",
        )
        login_session = FakeAsyncSession(
            FakeAsyncResponse({"token": "async-session-token"})
        )
        devices_session = FakeAsyncSession(FakeAsyncResponse([{"gw": "gateway-1"}]))

        async def connect_and_discover():
            self.assertTrue(await api.async_connect())
            return await api.async_get_detailed_devices()

        with patch(
            "ariston.ariston_api.aiohttp.ClientSession",
            side_effect=[login_session, devices_session],
        ) as client_session:
            devices = asyncio.run(connect_and_discover())

        # Every async request must set an explicit total timeout instead of
        # relying on aiohttp's 5 minute default.
        self.assertEqual(client_session.call_count, 2)
        for call in client_session.call_args_list:
            self.assertEqual(call.kwargs["timeout"], aiohttp.ClientTimeout(total=30))

        self.assertEqual(devices, [{"gw": "gateway-1"}])
        self.assertEqual(
            login_session.calls[0][0],
            ("POST", "https://example.test/api/accounts/login"),
        )
        self.assertEqual(
            login_session.calls[0][1]["json"],
            {"usr": "user@example.com", "pwd": "password"},
        )
        self.assertEqual(
            devices_session.calls[0][0],
            ("GET", "https://example.test/api/remote/plants"),
        )
        self.assertEqual(
            devices_session.calls[0][1]["headers"]["ar.authToken"],
            "async-session-token",
        )

    def test_not_found_device_endpoint_returns_empty_list(self):
        api = AristonAPI("user", "password")

        with patch(
            "ariston.ariston_api.requests.request",
            return_value=FakeResponse(status_code=404),
        ):
            self.assertEqual(api.get_detailed_devices(), [])

    def test_expired_token_is_refreshed_and_request_retried(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        responses = [
            FakeResponse(status_code=405),
            FakeResponse({"token": "refreshed-token"}),
            FakeResponse([{"gw": "gateway-1"}]),
        ]

        with patch(
            "ariston.ariston_api.requests.request", side_effect=responses
        ) as request:
            devices = api.get_detailed_devices()

        self.assertEqual(devices, [{"gw": "gateway-1"}])
        self.assertEqual(request.call_count, 3)
        self.assertEqual(
            request.call_args_list[-1].kwargs["headers"]["ar.authToken"],
            "refreshed-token",
        )

    def test_rate_limit_is_reported_as_connection_exception(self):
        api = AristonAPI("user", "password")

        with patch(
            "ariston.ariston_api.requests.request",
            return_value=FakeResponse(status_code=429, content=b"rate limited"),
        ):
            with self.assertRaises(ConnectionException) as error:
                api.get_detailed_devices()

        self.assertEqual(error.exception.args, (429, "rate limited"))

    def test_sync_read_endpoints_return_payloads_and_empty_defaults(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        features = {DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1}]}
        endpoints = (
            ("get_detailed_devices", (), "_get", "/remote/plants", [], []),
            ("get_detailed_velis_devices", (), "_get", "/velis/plants", [], []),
            ("get_devices", (), "_get", "/remote/plants/lite", [], []),
            ("get_features_for_device", ("gw-1",), "_get", "/gw-1/features", {}, {}),
            ("get_energy_account", ("gw-1",), "_get", "/energyAccount", {}, {}),
            ("get_consumptions_sequences", ("gw-1", "Dhw"), "_get", "/consSequencesApi8?usages=Dhw", [], []),
            ("get_consumptions_settings", ("gw-1",), "_post", "/getConsumptionsSettings", {}, {}),
            ("get_properties", ("gw-1", features, "en", "metric"), "_post", "/get?umsys=metric", {}, {}),
            ("get_bsb_plant_data", ("gw-1",), "_get", "/gw-1", {}, {}),
            ("get_velis_plant_data", (PlantData.Med, "gw-1"), "_get", "/gw-1", {}, {}),
            ("get_velis_plant_settings", (PlantData.Med, "gw-1"), "_get", "/plantSettings", {}, {}),
            ("get_menu_items", ("gw-1",), "_get", "/gw-1?menuItems=", [], []),
            ("get_thermostat_time_progs", ("gw-1", 2, "metric"), "_get", "/ChZn2?umsys=metric", {}, {}),
            ("get_bus_errors", ("gw-1",), "_get", "gatewayId=gw-1", [], []),
        )
        payload = [{"sample": "value"}]

        for name, args, transport, path_part, nonempty_default, empty_default in endpoints:
            with self.subTest(endpoint=name, response="payload"):
                response = payload if isinstance(nonempty_default, list) else payload[0]
                with patch.object(api, transport, return_value=response) as request:
                    result = getattr(api, name)(*args)
                self.assertEqual(result, response)
                self.assertIn(path_part, request.call_args.args[0])
            with self.subTest(endpoint=name, response="empty"):
                with patch.object(api, transport, return_value=None) as request:
                    result = getattr(api, name)(*args)
                self.assertEqual(result, empty_default)
                self.assertIn(path_part, request.call_args.args[0])

        items = api.get_items(features)
        self.assertTrue(any(item["id"].startswith("Zone") for item in items))

    def test_sync_write_endpoints_send_values_to_transport(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        writes = (
            ("set_consumptions_settings", ("gw-1", {"elecCost": 0.2})),
            ("set_property", ("gw-1", 2, {"x": True}, "ZoneDesiredTemp", 20, 19, "metric")),
            ("set_evo_number_of_showers", ("gw-1", 2)),
            ("set_evo_mode", ("gw-1", EvoPlantMode.MANUAL)),
            ("set_lydos_mode", ("gw-1", LydosPlantMode.GREEN)),
            ("set_nuos_mode", ("gw-1", NuosSplitOperativeMode.FAST)),
            ("set_bsb_mode", ("gw-1", BsbOperativeMode.ON)),
            ("set_bsb_zone_mode", ("gw-1", 2, BsbZoneMode.MANUAL, BsbZoneMode.OFF, False)),
            ("set_evo_temperature", ("gw-1", 55)),
            ("set_lydos_temperature", ("gw-1", 54)),
            ("set_nuos_temperature", ("gw-1", 55, 40, 50, 35)),
            ("set_bsb_temperature", ("gw-1", 55, 40, 50, 35)),
            ("set_bsb_zone_temperature", ("gw-1", 2, 22, 18, 21, 17, False)),
            ("set_nous_boost", ("gw-1", True)),
            ("set_evo_eco_mode", ("gw-1", True)),
            ("set_lux_power_option", ("gw-1", False)),
            ("set_velis_power", (PlantData.Med, "gw-1", True)),
            ("set_velis_plant_setting", (PlantData.Med, "gw-1", "setting", 2, 1)),
            ("set_holiday", ("gw-1", "2026-12-31")),
        )
        for name, args in writes:
            with self.subTest(endpoint=name):
                with patch.object(api, "_post") as post:
                    result = getattr(api, name)(*args)
                self.assertIsNone(result)
                post.assert_called_once()
                self.assertIn("gw-1", post.call_args.args[0])

    def test_sync_velis_slp_holiday_endpoint_sends_date_or_clear_value(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        endpoint = "https://example.test/api/velis/slpPlantData/gw-1/holiday"

        for holiday_end_date in ("2026-12-31T00:00:00", None):
            with self.subTest(holiday_end_date=holiday_end_date):
                with patch.object(api, "_post") as post:
                    result = api.set_velis_slp_holiday("gw-1", holiday_end_date)

                self.assertIsNone(result)
                post.assert_called_once_with(endpoint, {"new": holiday_end_date})

    def test_sync_request_empty_response_and_retry_failure_paths(self):
        api = AristonAPI("user", "password")
        request = api._AristonAPI__request

        with patch("ariston.ariston_api.requests.request", return_value=FakeResponse()):
            self.assertIsNone(request("GET", "https://example.test/empty"))

        with patch("ariston.ariston_api.time.sleep") as sleep, patch(
            "ariston.ariston_api.requests.request",
            side_effect=[FakeResponse(status_code=500), FakeResponse({"ok": True})],
        ) as send:
            self.assertEqual(request("GET", "https://example.test/retry"), {"ok": True})
        sleep.assert_called_once_with(5)
        self.assertEqual(send.call_count, 2)

        with patch(
            "ariston.ariston_api.requests.request",
            return_value=FakeResponse(status_code=503),
        ):
            with self.assertRaises(ConnectionException) as error:
                request("GET", "https://example.test/retry-fails", is_retry=True)
        self.assertEqual(error.exception.args, (503,))

        with patch.object(api, "connect", return_value=False), patch(
            "ariston.ariston_api.requests.request",
            return_value=FakeResponse(status_code=405),
        ):
            with self.assertRaisesRegex(ConnectionException, "Login failed"):
                request("GET", "https://example.test/login-retry")

        with patch(
            "ariston.ariston_api.requests.request",
            return_value=FakeResponse(status_code=405),
        ):
            with self.assertRaisesRegex(ConnectionException, "Invalid token"):
                request("GET", "https://example.test/invalid-token", is_retry=True)

    def test_sync_connect_returns_false_and_wraps_transport_errors(self):
        api = AristonAPI("user", "password")
        with patch.object(api, "_post", return_value=None):
            self.assertFalse(api.connect())
        with patch.object(api, "_post", side_effect=RuntimeError("offline")):
            with self.assertRaises(ConnectionException) as error:
                api.connect()
        self.assertIsInstance(error.exception.__cause__, RuntimeError)

    def test_async_connect_returns_false_and_wraps_transport_errors(self):
        api = AristonAPI("user", "password")

        async def exercise():
            with patch.object(api, "_async_post", new=AsyncMock(return_value=None)):
                self.assertFalse(await api.async_connect())
            with patch.object(api, "_async_post", new=AsyncMock(side_effect=RuntimeError("offline"))):
                with self.assertRaises(ConnectionException) as error:
                    await api.async_connect()
            self.assertIsInstance(error.exception.__cause__, RuntimeError)

        asyncio.run(exercise())

    def test_async_read_endpoints_return_payloads_and_empty_defaults(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        features = {DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1}]}
        endpoints = (
            ("async_get_detailed_devices", (), "/remote/plants", [], []),
            ("async_get_detailed_velis_devices", (), "/velis/plants", [], []),
            ("async_get_devices", (), "/remote/plants/lite", [], []),
            ("async_get_features_for_device", ("gw-1",), "/gw-1/features", None, None),
            ("async_get_energy_account", ("gw-1",), "/energyAccount", {}, {}),
            ("async_get_consumptions_sequences", ("gw-1", "Dhw"), "/consSequencesApi8?usages=Dhw", [], []),
            ("async_get_consumptions_settings", ("gw-1",), "/getConsumptionsSettings", {}, {}),
            ("async_get_properties", ("gw-1", features, "en", "metric"), "/get?umsys=metric", {}, {}),
            ("async_get_bsb_plant_data", ("gw-1",), "/gw-1", {}, {}),
            ("async_get_velis_plant_data", (PlantData.Med, "gw-1"), "/gw-1", {}, {}),
            ("async_get_velis_plant_settings", (PlantData.Med, "gw-1"), "/plantSettings", {}, {}),
            ("async_get_menu_items", ("gw-1",), "/gw-1?menuItems=", [], []),
            ("async_get_thermostat_time_progs", ("gw-1", 2, "metric"), "/ChZn2?umsys=metric", None, None),
            ("async_get_bus_errors", ("gw-1",), "gatewayId=gw-1", [], []),
        )
        payload = [{"sample": "value"}]

        async def exercise(name, args, response, empty):
            transport = (
                "_async_post"
                if name in {"async_get_consumptions_settings", "async_get_properties"}
                else "_async_get"
            )
            if empty is None:
                expected_nonempty = response
            elif isinstance(empty, list):
                expected_nonempty = response
            else:
                expected_nonempty = response
            for value, expected in ((response, expected_nonempty), (None, empty)):
                with patch.object(api, transport, new=AsyncMock(return_value=value)) as request:
                    result = await getattr(api, name)(*args)
                self.assertEqual(result, expected)
                self.assertIn(next(path for method, method_args, path, _, _ in endpoints if method == name), request.await_args.args[0])

        async def run_all():
            for name, args, _, nonempty_default, empty_default in endpoints:
                response = (
                    {"sample": "value"}
                    if nonempty_default is None or isinstance(empty_default, dict)
                    else payload
                )
                await exercise(name, args, response, empty_default)

        asyncio.run(run_all())

    def test_async_write_endpoints_send_values_to_transport(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        writes = (
            ("async_set_consumptions_settings", ("gw-1", {"elecCost": 0.2})),
            ("async_set_property", ("gw-1", 2, {"x": True}, "ZoneDesiredTemp", 20, 19, "metric")),
            ("async_set_evo_number_of_showers", ("gw-1", 2)),
            ("async_set_evo_mode", ("gw-1", EvoPlantMode.MANUAL)),
            ("async_set_lydos_mode", ("gw-1", LydosPlantMode.GREEN)),
            ("async_set_nuos_mode", ("gw-1", NuosSplitOperativeMode.FAST)),
            ("async_set_bsb_mode", ("gw-1", BsbOperativeMode.ON)),
            ("async_set_bsb_zone_mode", ("gw-1", 2, BsbZoneMode.MANUAL, BsbZoneMode.OFF, False)),
            ("async_set_evo_temperature", ("gw-1", 55)),
            ("async_set_lydos_temperature", ("gw-1", 54)),
            ("async_set_nuos_temperature", ("gw-1", 55, 40, 50, 35)),
            ("async_set_bsb_temperature", ("gw-1", 55, 40, 50, 35)),
            ("async_set_bsb_zone_temperature", ("gw-1", 2, 22, 18, 21, 17, False)),
            ("async_set_nous_boost", ("gw-1", True)),
            ("async_set_evo_eco_mode", ("gw-1", True)),
            ("async_set_lux_power_option", ("gw-1", False)),
            ("async_set_velis_power", (PlantData.Med, "gw-1", True)),
            ("async_set_velis_plant_setting", (PlantData.Med, "gw-1", "setting", 2, 1)),
            ("async_set_holiday", ("gw-1", "2026-12-31")),
        )

        async def run_all():
            for name, args in writes:
                with self.subTest(endpoint=name):
                    with patch.object(api, "_async_post", new=AsyncMock()) as post:
                        result = await getattr(api, name)(*args)
                    self.assertIsNone(result)
                    post.assert_awaited_once()
                    self.assertIn("gw-1", post.await_args.args[0])

        asyncio.run(run_all())

    def test_async_velis_slp_holiday_endpoint_sends_date_or_clear_value(self):
        api = AristonAPI("user", "password", api_url="https://example.test/api/")
        endpoint = "https://example.test/api/velis/slpPlantData/gw-1/holiday"

        async def run_all():
            for holiday_end_date in ("2026-12-31T00:00:00", None):
                with self.subTest(holiday_end_date=holiday_end_date):
                    with patch.object(api, "_async_post", new=AsyncMock()) as post:
                        result = await api.async_set_velis_slp_holiday(
                            "gw-1", holiday_end_date
                        )

                    self.assertIsNone(result)
                    post.assert_awaited_once_with(
                        endpoint, {"new": holiday_end_date}
                    )

        asyncio.run(run_all())

    def test_async_request_empty_response_and_retry_failure_paths(self):
        api = AristonAPI("user", "password")
        request = api._AristonAPI__async_request

        async def exercise():
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                side_effect=[FakeAsyncSession(FakeAsyncResponse())],
            ):
                self.assertIsNone(await request("GET", "https://example.test/empty"))

            with patch("ariston.ariston_api.asyncio.sleep", new=AsyncMock()) as sleep, patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                side_effect=[
                    FakeAsyncSession(FakeAsyncResponse(status_code=500)),
                    FakeAsyncSession(FakeAsyncResponse({"ok": True})),
                ],
            ):
                self.assertEqual(await request("GET", "https://example.test/retry"), {"ok": True})
            sleep.assert_awaited_once_with(5)

            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                return_value=FakeAsyncSession(FakeAsyncResponse(status_code=503)),
            ):
                with self.assertRaises(ConnectionException) as error:
                    await request("GET", "https://example.test/retry-fails", is_retry=True)
            self.assertEqual(error.exception.args, (503,))

            with patch.object(api, "async_connect", new=AsyncMock(return_value=False)), patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                return_value=FakeAsyncSession(FakeAsyncResponse(status_code=405)),
            ):
                with self.assertRaisesRegex(ConnectionException, "Login failed"):
                    await request("GET", "https://example.test/login-retry")

            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                return_value=FakeAsyncSession(FakeAsyncResponse(status_code=405)),
            ):
                with self.assertRaisesRegex(ConnectionException, "Invalid token"):
                    await request("GET", "https://example.test/invalid-token", is_retry=True)

            with patch.object(api, "async_connect", new=AsyncMock(return_value=True)), patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                side_effect=[
                    FakeAsyncSession(FakeAsyncResponse(status_code=405)),
                    FakeAsyncSession(FakeAsyncResponse({"ok": True})),
                ],
            ):
                self.assertEqual(
                    await request("GET", "https://example.test/refreshed-token"),
                    {"ok": True},
                )

            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                return_value=FakeAsyncSession(FakeAsyncResponse(status_code=404)),
            ):
                self.assertIsNone(await request("GET", "https://example.test/not-found"))

            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                return_value=FakeAsyncSession(FakeAsyncRateLimitedResponse()),
            ):
                with self.assertRaises(ConnectionException) as error:
                    await request("GET", "https://example.test/rate-limited")
            self.assertEqual(error.exception.args, (429, b"rate limited"))

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
