"""Unit tests for the 429 rate-limit handling in ariston.ariston_api."""

import asyncio
import time
import unittest
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from ariston.ariston_api import (
    AristonAPI,
    ConnectionException,
    RateLimitException,
    _parse_block_seconds,
)


def _api() -> AristonAPI:
    return AristonAPI("user", "pass")


def _sync_response(
    status: int,
    content: bytes = b"",
    json_data: Any = None,
    headers: Optional[dict[str, str]] = None,
):
    response = MagicMock()
    response.ok = status < 400
    response.status_code = status
    response.content = content
    response.headers = headers or {}
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
        self,
        status: int,
        payload: bytes = b"",
        json_data: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status = status
        self.headers = headers or {}
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


def _yielding_session_cls(responses: list, calls: list):
    """Like _fake_session_cls, but lets other tasks run mid-request."""
    base = _fake_session_cls(responses, calls)

    class _Session(base):
        async def request(self, *args: Any, **kwargs: Any):
            calls.append(1)
            await asyncio.sleep(0)
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
        """A bare "Requests are blocked" must not be retried a few seconds later."""
        http = MagicMock(side_effect=[_sync_response(429, b"Requests are blocked")])
        sleeps: list[int] = []
        api = _api()
        with patch("ariston.ariston_api.requests.request", http), patch(
            "ariston.ariston_api.time.sleep", side_effect=sleeps.append
        ):
            with self.assertRaises(RateLimitException) as ctx:
                api._get("https://example/api")

        self.assertEqual(http.call_count, 1)  # no blind retry
        self.assertEqual(sleeps, [])
        self.assertEqual(ctx.exception.args[0], 429)  # ConnectionException shape
        self.assertIsInstance(ctx.exception, ConnectionException)
        self.assertEqual(ctx.exception.retry_after, 60)
        self.assertAlmostEqual(api._blocked_until, time.time() + 60, delta=2)

    def test_unknown_block_backoff_doubles_and_caps(self):
        api = _api()
        waits = []
        for _ in range(6):
            api._blocked_until = 0.0  # previous window has expired
            http = MagicMock(side_effect=[_sync_response(429, b"Requests are blocked")])
            with patch("ariston.ariston_api.requests.request", http):
                with self.assertRaises(RateLimitException) as ctx:
                    api._get("https://example/api")
            waits.append(ctx.exception.retry_after)

        self.assertEqual(waits, [60, 120, 240, 480, 900, 900])

    def test_success_resets_backoff(self):
        api = _api()
        http = MagicMock(
            side_effect=[
                _sync_response(429, b"Requests are blocked"),
                _sync_response(200, b"{}", {"ok": True}),
                _sync_response(429, b"Requests are blocked"),
            ]
        )
        with patch("ariston.ariston_api.requests.request", http):
            with self.assertRaises(RateLimitException):
                api._get("https://example/api")
            api._blocked_until = 0.0
            self.assertEqual(api._get("https://example/api"), {"ok": True})
            api._blocked_until = 0.0
            with self.assertRaises(RateLimitException) as ctx:
                api._get("https://example/api")

        self.assertEqual(ctx.exception.retry_after, 60)  # back to the base wait

    def test_retry_after_header_is_honoured(self):
        responses = [
            _sync_response(429, b"Requests are blocked", headers={"Retry-After": "20"}),
            _sync_response(200, b"{}", {"ok": True}),
        ]
        http = MagicMock(side_effect=responses)
        sleeps: list[int] = []
        with patch("ariston.ariston_api.requests.request", http), patch(
            "ariston.ariston_api.time.sleep", side_effect=sleeps.append
        ):
            result = _api()._get("https://example/api")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(sleeps, [21])

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
            with self.assertRaises(RateLimitException) as ctx:
                api._get("https://example/api")

        http.assert_not_called()  # no network call inside the block window
        self.assertAlmostEqual(ctx.exception.retry_after, 30, delta=2)

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

    def test_async_429_without_parsable_body_backs_off_without_retry(self):
        responses = [_FakeAiohttpResponse(429, b"Requests are blocked")]
        calls: list[int] = []
        sleeps: list[Optional[int]] = []
        api = _api()

        async def run() -> None:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ), patch(
                "ariston.ariston_api.asyncio.sleep", side_effect=sleeps.append
            ):
                await api._async_get("https://example/api")

        with self.assertRaises(RateLimitException) as ctx:
            asyncio.run(run())

        self.assertEqual(len(calls), 1)  # no blind retry
        self.assertEqual(sleeps, [])
        self.assertEqual(ctx.exception.retry_after, 60)

    def test_async_concurrent_429s_count_as_one_strike(self):
        """Gathered requests rejected by the same block must not double the wait."""
        responses = [
            _FakeAiohttpResponse(429, b"Requests are blocked"),
            _FakeAiohttpResponse(429, b"Requests are blocked"),
        ]
        calls: list[int] = []
        api = _api()

        async def run() -> list:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _yielding_session_cls(responses, calls),
            ):
                return await asyncio.gather(
                    api._async_get("https://example/a"),
                    api._async_get("https://example/b"),
                    return_exceptions=True,
                )

        results = asyncio.run(run())

        self.assertEqual(len(calls), 2)
        self.assertTrue(all(isinstance(r, RateLimitException) for r in results))
        self.assertEqual(api._rate_limit_strikes, 1)
        self.assertEqual([r.retry_after for r in results], [60, 60])

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


if __name__ == "__main__":
    unittest.main()
