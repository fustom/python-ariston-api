"""Unit tests for the 429 rate-limit handling in ariston.ariston_api."""

import asyncio
import time
import unittest
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from ariston.ariston_api import (
    RATE_LIMIT_BACKOFF_MAX_SECONDS,
    RATE_LIMIT_BACKOFF_START_SECONDS,
    AristonAPI,
    ConnectionException,
    _parse_block_seconds,
)


def _api() -> AristonAPI:
    return AristonAPI("user", "pass")


def _sync_response(status: int, content: bytes = b"", json_data: Any = None):
    response = MagicMock()
    response.ok = status < 400
    response.status_code = status
    response.content = content
    if json_data is not None:
        response.json.return_value = json_data
    return response


class _FakeAiohttpContent:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


class _FakeAiohttpResponse:
    def __init__(
        self, status: int, payload: bytes = b"", json_data: Any = None
    ) -> None:
        self.status = status
        self.ok = status < 400
        self.content = _FakeAiohttpContent(payload)
        self.content_length = len(payload)
        self._json_data = json_data

    async def json(self) -> Any:
        return self._json_data


def _fake_session_cls(responses: list, calls: list):
    class _Session:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_Session":
            return self

        async def __aexit__(self, *exc: Any) -> bool:
            return False

        async def request(self, *args: Any, **kwargs: Any):
            calls.append(1)
            return responses.pop(0)

    return _Session


class RateLimitTests(unittest.TestCase):
    """429 handling: parse, sleep-out with a single retry, per-instance window."""

    # -- parse helper --

    def test_parse_block_seconds(self):
        self.assertEqual(
            _parse_block_seconds(b"Requests are blocked for 66 seconds"), 66
        )
        self.assertEqual(_parse_block_seconds(b"Requests are blocked for 5 seconds"), 5)
        self.assertIsNone(_parse_block_seconds(b"Too many requests"))

    # -- sync path (requests) --

    def test_429_parses_wait_seconds(self):
        responses = [
            _sync_response(429, b"Requests are blocked for 66 seconds"),
            _sync_response(200, b"{}", {"ok": True}),
        ]
        http = MagicMock(side_effect=responses)
        sleeps: list[int] = []
        api = _api()
        with patch("ariston.ariston_api.requests.request", http), patch(
            "ariston.ariston_api.time.sleep", side_effect=sleeps.append
        ):
            result = api._get("https://example/api")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(http.call_count, 2)  # exactly one retry
        self.assertEqual(sleeps, [67])  # parsed 66 + 1s margin
        self.assertGreater(api._blocked_until, 0)  # block window was set

    def test_429_without_parsable_body_backs_off_without_retry(self):
        http = MagicMock(side_effect=[_sync_response(429, b"Requests are blocked")])
        sleeps: list[int] = []
        api = _api()
        with patch("ariston.ariston_api.requests.request", http), patch(
            "ariston.ariston_api.time.sleep", side_effect=sleeps.append
        ), patch("ariston.ariston_api.time.time", return_value=1000.0):
            with self.assertRaises(ConnectionException):
                api._get("https://example/api")

        self.assertEqual(http.call_count, 1)  # no retry while blocked
        self.assertEqual(sleeps, [])
        self.assertEqual(api._blocked_until, 1000.0 + RATE_LIMIT_BACKOFF_START_SECONDS)

    def test_429_twice_raises(self):
        body = b"Requests are blocked for 10 seconds"
        http = MagicMock(
            side_effect=[_sync_response(429, body), _sync_response(429, body)]
        )
        api = _api()
        with patch("ariston.ariston_api.requests.request", http), patch(
            "ariston.ariston_api.time.sleep"
        ):
            with self.assertRaises(ConnectionException):
                api._get("https://example/api")

        self.assertEqual(http.call_count, 2)  # one retry, then raise

    def test_blocked_until_short_circuits(self):
        api = _api()
        api._blocked_until = time.time() + 30
        http = MagicMock()
        with patch("ariston.ariston_api.requests.request", http):
            with self.assertRaises(ConnectionException):
                api._get("https://example/api")

        http.assert_not_called()  # no network call inside the block window

    def test_block_window_is_per_instance(self):
        """A 429 on one instance must not silence other instances."""
        blocked = _api()
        other = _api()
        http = MagicMock(
            side_effect=[
                _sync_response(429, b"Requests are blocked for 30 seconds"),
                _sync_response(200, b"{}", {"ok": True}),
            ]
        )
        with patch("ariston.ariston_api.requests.request", http), patch(
            "ariston.ariston_api.time.sleep"
        ):
            self.assertEqual(blocked._get("https://example/api"), {"ok": True})

        self.assertGreater(blocked._blocked_until, 0)
        self.assertEqual(other._blocked_until, 0.0)  # untouched by the 429

    # -- async path (aiohttp) --

    def test_async_429_parses_and_retries(self):
        responses = [
            _FakeAiohttpResponse(429, b"Requests are blocked for 66 seconds"),
            _FakeAiohttpResponse(200, b"{}", {"ok": True}),
        ]
        calls: list[int] = []
        sleeps: list[Optional[int]] = []

        async def run() -> Any:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ), patch(
                "ariston.ariston_api.asyncio.sleep", side_effect=sleeps.append
            ):
                return await _api()._async_get("https://example/api")

        result = asyncio.run(run())

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(calls), 2)  # exactly one retry
        self.assertEqual(sleeps, [67])  # parsed 66 + 1s margin

    def test_async_blocked_until_short_circuits(self):
        calls: list[int] = []
        api = _api()
        api._blocked_until = time.time() + 30

        async def run() -> None:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls([], calls),
            ):
                with self.assertRaises(ConnectionException):
                    await api._async_get("https://example/api")

        asyncio.run(run())

        self.assertEqual(calls, [])  # no network call inside the block window

    def test_async_block_window_is_per_instance(self):
        """Async twin: a 429 on one instance must not silence other instances."""
        blocked = _api()
        other = _api()
        responses = [
            _FakeAiohttpResponse(429, b"Requests are blocked for 30 seconds"),
            _FakeAiohttpResponse(200, b"{}", {"ok": True}),
        ]
        calls: list[int] = []

        async def run() -> Any:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ), patch("ariston.ariston_api.asyncio.sleep"):
                return await blocked._async_get("https://example/api")

        self.assertEqual(asyncio.run(run()), {"ok": True})

        self.assertGreater(blocked._blocked_until, 0)
        self.assertEqual(other._blocked_until, 0.0)  # untouched by the 429


    def test_async_429_without_duration_backs_off_doubles_and_caps(self):
        api = _api()
        calls: list[int] = []
        sleeps: list[Optional[int]] = []
        waits: list[float] = []

        async def blocked_request() -> None:
            responses = [_FakeAiohttpResponse(429, b"Requests are blocked")]
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ), patch(
                "ariston.ariston_api.asyncio.sleep", side_effect=sleeps.append
            ), patch("ariston.ariston_api.time.time", return_value=1000.0):
                with self.assertRaises(ConnectionException):
                    await api._async_get("https://example/api")

        for _ in range(5):
            api._blocked_until = 0.0  # the previous pause has ended
            asyncio.run(blocked_request())
            waits.append(api._blocked_until - 1000.0)

        start = RATE_LIMIT_BACKOFF_START_SECONDS
        self.assertEqual(waits, [start, 2 * start, 4 * start, 8 * start, 8 * start])
        self.assertEqual(waits[-1], RATE_LIMIT_BACKOFF_MAX_SECONDS)
        self.assertEqual(len(calls), 5)  # one request per pause, no retries
        self.assertEqual(sleeps, [])

    def test_async_success_resets_backoff(self):
        api = _api()
        api._rate_limit_backoff_seconds = 4 * RATE_LIMIT_BACKOFF_START_SECONDS
        calls: list[int] = []

        async def run(responses: list) -> Any:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ), patch("ariston.ariston_api.time.time", return_value=1000.0):
                return await api._async_get("https://example/api")

        self.assertEqual(
            asyncio.run(run([_FakeAiohttpResponse(200, b"{}", {"ok": True})])),
            {"ok": True},
        )
        self.assertEqual(api._rate_limit_backoff_seconds, 0)

        with self.assertRaises(ConnectionException):
            asyncio.run(run([_FakeAiohttpResponse(429, b"Requests are blocked")]))
        self.assertEqual(api._blocked_until, 1000.0 + RATE_LIMIT_BACKOFF_START_SECONDS)


if __name__ == "__main__":
    unittest.main()
