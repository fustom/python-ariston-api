"""Tests for authenticated cloud API requests."""

import asyncio
import unittest
from unittest.mock import patch

from ariston.ariston_api import AristonAPI, ConnectionException


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
        ):
            devices = asyncio.run(connect_and_discover())

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


if __name__ == "__main__":
    unittest.main()
