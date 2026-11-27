"""Unit tests for the 429 rate-limit handling in ariston.ariston_api."""

import asyncio
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from ariston.ariston_api import (
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


class _FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[int] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: int) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class RateLimitTests(unittest.TestCase):
    """429 handling: parse, sleep-out with a single retry, per-instance window."""

    def setUp(self) -> None:
        self.clock = _FakeClock()
        self.real_sleep = asyncio.sleep
        self.enterContext(patch("ariston.ariston_api.time", self.clock))
        self.enterContext(
            patch(
                "ariston.ariston_api.asyncio.sleep",
                side_effect=lambda seconds: self.clock.sleep(seconds),
            )
        )

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
        api = _api()
        with patch("ariston.ariston_api.requests.request", http):
            result = api._get("https://example/api")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(http.call_count, 2)  # exactly one retry
        self.assertEqual(self.clock.sleeps, [67])  # parsed 66 + 1s margin
        self.assertGreater(api._blocked_until, 0)  # block window was set

    def test_429_without_parsable_body(self):
        http = MagicMock(return_value=_sync_response(429, b"Too many requests"))
        api = _api()
        with patch("ariston.ariston_api.requests.request", http):
            with self.assertRaises(ConnectionException) as ctx:
                api._get("https://example/api")

        self.assertEqual(ctx.exception.args, (429, "Too many requests"))
        self.assertEqual(ctx.exception.retry_after, 60.0)
        self.assertEqual(self.clock.sleeps, [])  # immediate cooldown, no blind 5s retry
        self.assertEqual(http.call_count, 1)
        self.assertEqual(api._rate_limit_streak, 1)
        self.assertEqual(api._blocked_until, self.clock.time() + 60)

    def test_429_twice_raises(self):
        body = b"Requests are blocked for 10 seconds"
        http = MagicMock(
            side_effect=[_sync_response(429, body), _sync_response(429, body)]
        )
        api = _api()
        with patch("ariston.ariston_api.requests.request", http):
            with self.assertRaises(ConnectionException):
                api._get("https://example/api")

        self.assertEqual(http.call_count, 2)  # one retry, then raise

    def test_blocked_until_short_circuits(self):
        api = _api()
        api._blocked_until = self.clock.time() + 30
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
        with patch("ariston.ariston_api.requests.request", http):
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

        async def run() -> Any:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ):
                return await _api()._async_get("https://example/api")

        result = asyncio.run(run())

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(calls), 2)  # exactly one retry
        self.assertEqual(self.clock.sleeps, [67])  # parsed 66 + 1s margin

    def test_async_blocked_until_short_circuits(self):
        calls: list[int] = []
        api = _api()
        api._blocked_until = self.clock.time() + 30

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
            ):
                return await blocked._async_get("https://example/api")

        self.assertEqual(asyncio.run(run()), {"ok": True})

        self.assertGreater(blocked._blocked_until, 0)
        self.assertEqual(other._blocked_until, 0.0)  # untouched by the 429

    def test_429_without_duration_escalates_cooldown_and_resets_on_ok(self):
        api = _api()
        body = b"Requests are blocked"
        http = MagicMock(
            side_effect=[
                _sync_response(429, body),
                _sync_response(429, body),
                _sync_response(200, b"{}", {"ok": True}),
            ]
        )
        with patch("ariston.ariston_api.requests.request", http):
            with self.assertRaises(ConnectionException) as first_err:
                api._get("https://example/api")
            self.assertEqual(first_err.exception.retry_after, 60.0)
            self.assertEqual(api._blocked_until - self.clock.time(), 60.0)
            self.assertEqual(api._rate_limit_streak, 1)
            self.assertEqual(self.clock.sleeps, [])

            self.clock.now += 60
            with self.assertRaises(ConnectionException) as second_err:
                api._get("https://example/api")
            self.assertEqual(second_err.exception.retry_after, 120.0)
            self.assertEqual(api._blocked_until - self.clock.time(), 120.0)
            self.assertEqual(api._rate_limit_streak, 2)
            self.assertEqual(self.clock.sleeps, [])

            self.clock.now += 120
            self.assertEqual(api._get("https://example/api"), {"ok": True})
            self.assertEqual(api._rate_limit_streak, 0)
        self.assertEqual(http.call_count, 3)

    def test_async_429_without_duration_sets_cooldown_and_retry_after_header(self):
        api = _api()
        resp_with_header = _FakeAiohttpResponse(429, b"Requests are blocked")
        resp_with_header.headers = {"Retry-After": "12"}
        responses = [
            resp_with_header,
            _FakeAiohttpResponse(200, b"{}", {"ok": True}),
            _FakeAiohttpResponse(429, b"Requests are blocked"),
        ]
        calls: list[int] = []

        async def run():
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(responses, calls),
            ):
                ok = await api._async_get("https://example/api")
                api._blocked_until = 0.0
                with self.assertRaises(ConnectionException) as ctx:
                    await api._async_get("https://example/api")
                return ok, ctx.exception

        ok, exc = asyncio.run(run())
        self.assertEqual(ok, {"ok": True})
        self.assertEqual(exc.args, (429, b"Requests are blocked"))
        self.assertEqual(exc.retry_after, 60.0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.clock.sleeps, [13])
        self.assertEqual(api._rate_limit_streak, 1)
        self.assertEqual(api._blocked_until - self.clock.time(), 60.0)

    def test_async_overlapping_429_sends_single_retry(self):
        api = _api()
        body = b"Requests are blocked for 5 seconds"
        responses = [
            _FakeAiohttpResponse(429, body),
            _FakeAiohttpResponse(429, body),
            _FakeAiohttpResponse(429, b"Requests are blocked"),
        ]
        calls: list[int] = []

        async def run():
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                self._overlapping_session_cls(responses, calls, self.real_sleep),
            ), patch(
                "ariston.ariston_api.asyncio.sleep", side_effect=self._overlapping_sleep
            ):
                return await asyncio.gather(
                    api._async_get("https://example/api/a"),
                    api._async_get("https://example/api/b"),
                    return_exceptions=True,
                )

        results = asyncio.run(run())
        self.assertEqual(len(calls), 3)  # 2 initial calls + 1 single claimed retry
        self.assertEqual(self.clock.sleeps, [6, 6])
        self.assertEqual(api._rate_limit_streak, 1)
        self.assertTrue(all(isinstance(res, ConnectionException) for res in results))

    async def _run_overlapping_gets(
        self, api: AristonAPI, responses: list, calls: list[int]
    ) -> list[Any]:
        with patch(
            "ariston.ariston_api.aiohttp.ClientSession",
            self._overlapping_session_cls(responses, calls, self.real_sleep),
        ):
            return await asyncio.gather(
                api._async_get("https://example/api/a"),
                api._async_get("https://example/api/b"),
                return_exceptions=True,
            )

    def test_async_overlapping_unparsable_429_escalates_cooldown_once(self):
        for initial_streak, expected_streak, expected_cooldown in (
            (0, 1, 60.0),
            (1, 2, 120.0),
        ):
            with self.subTest(initial_streak=initial_streak):
                api = _api()
                api._rate_limit_streak = initial_streak
                responses = [
                    _FakeAiohttpResponse(429, b"Requests are blocked"),
                    _FakeAiohttpResponse(429, b"Requests are blocked"),
                ]
                calls: list[int] = []
                self.clock.sleeps.clear()

                results = asyncio.run(
                    self._run_overlapping_gets(api, responses, calls)
                )
                self.assertEqual(len(calls), 2)
                self.assertEqual(self.clock.sleeps, [])
                self.assertEqual(api._rate_limit_streak, expected_streak)
                self.assertEqual(
                    api._blocked_until - self.clock.time(), expected_cooldown
                )
                for res in results:
                    self.assertIsInstance(res, ConnectionException)
                    self.assertEqual(res.retry_after, expected_cooldown)

    async def _overlapping_sleep(self, seconds: int) -> None:
        self.clock.sleeps.append(seconds)
        wake_at = self.clock.now + seconds
        await self.real_sleep(0)
        self.clock.now = max(self.clock.now, wake_at)

    @staticmethod
    def _overlapping_session_cls(responses: list, calls: list, real_sleep: Any):
        class _Session:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def __aenter__(self) -> "_Session":
                return self

            async def __aexit__(self, *exc: Any) -> bool:
                return False

            async def request(self, *args: Any, **kwargs: Any):
                calls.append(1)
                await real_sleep(0)
                return responses.pop(0)

        return _Session

    def test_retry_after_still_retries_when_streak_is_nonzero(self):
        for is_async in (False, True):
            with self.subTest(is_async=is_async):
                api = _api()
                api._rate_limit_streak = 1
                self.clock.sleeps.clear()
                if not is_async:
                    r1 = _sync_response(429, b"Requests are blocked")
                    r1.headers = {"Retry-After": "8"}
                    http = MagicMock(
                        side_effect=[r1, _sync_response(200, b"{}", {"ok": True})]
                    )
                    with patch("ariston.ariston_api.requests.request", http):
                        result = api._get("https://example/api")
                    self.assertEqual(http.call_count, 2)
                else:
                    r1 = _FakeAiohttpResponse(429, b"Requests are blocked")
                    r1.headers = {"Retry-After": "8"}
                    responses = [r1, _FakeAiohttpResponse(200, b"{}", {"ok": True})]
                    calls: list[int] = []

                    async def run_async():
                        with patch(
                            "ariston.ariston_api.aiohttp.ClientSession",
                            _fake_session_cls(responses, calls),
                        ):
                            return await api._async_get("https://example/api")

                    result = asyncio.run(run_async())
                    self.assertEqual(len(calls), 2)

                self.assertEqual(result, {"ok": True})
                self.assertEqual(self.clock.sleeps, [9])
                self.assertEqual(api._rate_limit_streak, 0)

    def test_async_overlapping_429_respects_longest_shared_deadline(self):
        for order in ("long_first", "short_first"):
            with self.subTest(order=order):
                api = _api()
                r_long = _FakeAiohttpResponse(429, b"Requests are blocked")
                r_long.headers = {"Retry-After": "60"}
                r_short = _FakeAiohttpResponse(429, b"Requests are blocked")
                r_short.headers = {"Retry-After": "1"}
                responses = (
                    [r_long, r_short, _FakeAiohttpResponse(200, b"{}", {"ok": True})]
                    if order == "long_first"
                    else [r_short, r_long, _FakeAiohttpResponse(200, b"{}", {"ok": True})]
                )
                calls: list[int] = []
                self.clock.sleeps.clear()

                async def run():
                    with patch(
                        "ariston.ariston_api.aiohttp.ClientSession",
                        self._overlapping_session_cls(responses, calls, self.real_sleep),
                    ), patch(
                        "ariston.ariston_api.asyncio.sleep",
                        side_effect=self._overlapping_sleep,
                    ):
                        return await asyncio.gather(
                            api._async_get("https://example/api/a"),
                            api._async_get("https://example/api/b"),
                            return_exceptions=True,
                        )

                results = asyncio.run(run())
                self.assertEqual(len(calls), 3)
                if order == "long_first":
                    self.assertEqual(self.clock.sleeps, [61, 61])
                    self.assertEqual(results[0], {"ok": True})
                    self.assertIsInstance(results[1], ConnectionException)
                else:
                    self.assertEqual(self.clock.sleeps, [2, 61])
                    self.assertIsInstance(results[0], ConnectionException)
                    self.assertEqual(results[1], {"ok": True})

    def test_async_late_retry_after_preserves_block_after_successful_retry(self):
        api = _api()
        owner_url = "https://example/api/owner"
        late_url = "https://example/api/late"
        next_url = "https://example/api/next"
        first_response = _FakeAiohttpResponse(429, b"Requests are blocked for 1 seconds")
        late_response = _FakeAiohttpResponse(429, b"Requests are blocked")
        late_response.headers = {"Retry-After": "60"}
        ok = _FakeAiohttpResponse(200, b"{}", {"ok": True})
        calls: list[str] = []

        async def run() -> None:
            late_request_started = asyncio.Event()
            retry_started = asyncio.Event()

            async def request(_method: str, url: str, **kwargs: Any):
                calls.append(url)
                if url == late_url:
                    late_request_started.set()
                    await retry_started.wait()
                    return late_response
                if url == owner_url:
                    if calls.count(owner_url) == 1:
                        return first_response
                    retry_started.set()
                    with self.assertRaises(ConnectionException):
                        await late_request
                return ok

            with patch("ariston.ariston_api.aiohttp.ClientSession") as session:
                session.return_value.__aenter__.return_value.request = AsyncMock(
                    side_effect=request
                )
                late_request = asyncio.create_task(api._async_get(late_url))
                await late_request_started.wait()
                self.assertEqual(await api._async_get(owner_url), {"ok": True})

                self.clock.now += 60.75
                with self.assertRaises(ConnectionException):
                    await api._async_get(next_url)
                self.clock.now += 0.25
                self.assertEqual(await api._async_get(next_url), {"ok": True})

        asyncio.run(asyncio.wait_for(run(), timeout=5))
        self.assertEqual(calls, [late_url, owner_url, owner_url, next_url])

    def test_retry_waits_for_shared_deadline(self):
        url = "https://example/api"
        body = b"Requests are blocked for 1 seconds"

        def wake_early(seconds: int) -> None:
            self.assertEqual(seconds, 2)
            self.clock.now += 0.25

        with patch.object(self.clock, "sleep", side_effect=wake_early):
            with self.subTest(transport="sync"):
                http = MagicMock(
                    side_effect=[
                        _sync_response(429, body),
                        _sync_response(200, b"{}", {"ok": True}),
                    ]
                )
                with patch("ariston.ariston_api.requests.request", http):
                    with self.assertRaises(ConnectionException):
                        _api()._get(url)
                http.assert_called_once()

            with self.subTest(transport="async"):
                calls: list[int] = []
                responses = [
                    _FakeAiohttpResponse(429, body),
                    _FakeAiohttpResponse(200, b"{}", {"ok": True}),
                ]

                async def run() -> None:
                    with patch(
                        "ariston.ariston_api.aiohttp.ClientSession",
                        _fake_session_cls(responses, calls),
                    ):
                        with self.assertRaises(ConnectionException):
                            await _api()._async_get(url)

                asyncio.run(run())
                self.assertEqual(len(calls), 1)

    async def _async_get_expecting_connection_error(
        self, api: AristonAPI, url: str = "https://example/api"
    ) -> ConnectionException:
        with self.assertRaises(ConnectionException) as ctx:
            await api._async_get(url)
        return ctx.exception

    def test_short_circuit_rate_limit_exposes_retry_after(self):
        for is_async in (False, True):
            with self.subTest(is_async=is_async):
                api = _api()
                api._blocked_until = self.clock.time() + 45.5

                if not is_async:
                    with self.assertRaises(ConnectionException) as ctx:
                        api._get("https://example/api")
                    exc = ctx.exception
                else:
                    exc = asyncio.run(
                        self._async_get_expecting_connection_error(api)
                    )

                self.assertEqual(exc.args[0], 429)
                self.assertEqual(exc.retry_after, 45.5)

    def test_repeated_parsed_429_exposes_retry_after(self):
        body = b"Requests are blocked for 10 seconds"
        http = MagicMock(
            side_effect=[_sync_response(429, body), _sync_response(429, body)]
        )
        api = _api()
        with patch("ariston.ariston_api.requests.request", http):
            with self.assertRaises(ConnectionException) as ctx:
                api._get("https://example/api")
        self.assertEqual(ctx.exception.args[0], 429)
        self.assertEqual(ctx.exception.retry_after, 11.0)

    def test_ok_response_during_active_block_preserves_streak(self):
        api = _api()
        api._rate_limit_streak = 2
        api._blocked_until = self.clock.time() + 60.0
        with patch(
            "ariston.ariston_api.requests.request",
            return_value=_sync_response(200, b"{}", {"ok": True}),
        ):
            result = api._AristonAPI__request(
                "GET", "https://example/api", rate_limit_retry=True
            )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(api._rate_limit_streak, 2)

        async_api = _api()
        async_api._rate_limit_streak = 1
        responses = [
            _FakeAiohttpResponse(429, b"Requests are blocked"),
            _FakeAiohttpResponse(200, b"{}", {"ok": True}),
        ]
        calls: list[int] = []
        results = asyncio.run(
            self._run_overlapping_gets(async_api, responses, calls)
        )
        self.assertIsInstance(results[0], ConnectionException)
        self.assertEqual(results[1], {"ok": True})
        self.assertEqual(async_api._rate_limit_streak, 2)

    def test_async_5xx_retry_respects_active_rate_limit_block(self):
        api = _api()
        calls: list[str] = []
        sleep_started = asyncio.Event()
        block_active = asyncio.Event()

        async def fake_sleep(seconds: int) -> None:
            self.clock.sleeps.append(seconds)
            sleep_started.set()
            await block_active.wait()
            self.clock.now += seconds

        async def request(_method: str, url: str, **kwargs: Any):
            calls.append(url)
            if url.endswith("/five-hundred"):
                return _FakeAiohttpResponse(500)
            return _FakeAiohttpResponse(429, b"Requests are blocked")

        async def run():
            with patch("ariston.ariston_api.aiohttp.ClientSession") as session, patch(
                "ariston.ariston_api.asyncio.sleep", side_effect=fake_sleep
            ):
                session.return_value.__aenter__.return_value.request = AsyncMock(
                    side_effect=request
                )
                task_500 = asyncio.create_task(
                    api._async_get("https://example/api/five-hundred")
                )
                await sleep_started.wait()
                with self.assertRaises(ConnectionException) as err_429:
                    await api._async_get("https://example/api/four-two-nine")
                block_active.set()
                with self.assertRaises(ConnectionException) as err_500:
                    await task_500
                return err_429.exception, err_500.exception

        err_429, err_500 = asyncio.run(asyncio.wait_for(run(), timeout=5))
        self.assertEqual(
            calls,
            [
                "https://example/api/five-hundred",
                "https://example/api/four-two-nine",
            ],
        )  # 500 retry did not hit server during active 429 block
        self.assertEqual(api._rate_limit_streak, 1)
        self.assertEqual(err_429.retry_after, 60.0)
        self.assertEqual(err_500.args[0], 429)
        self.assertEqual(err_500.retry_after, 55.0)

    def test_connect_preserves_rate_limit_exception_and_retry_after(self):
        sync_api = _api()
        with patch(
            "ariston.ariston_api.requests.request",
            return_value=_sync_response(429, b"Requests are blocked"),
        ):
            with self.assertRaises(ConnectionException) as sync_ctx:
                sync_api.connect()
        self.assertEqual(sync_ctx.exception.args, (429, "Requests are blocked"))
        self.assertEqual(sync_ctx.exception.retry_after, 60.0)

        async_api = _api()
        calls: list[int] = []

        async def run_connect() -> ConnectionException:
            with patch(
                "ariston.ariston_api.aiohttp.ClientSession",
                _fake_session_cls(
                    [_FakeAiohttpResponse(429, b"Requests are blocked")], calls
                ),
            ):
                with self.assertRaises(ConnectionException) as ctx:
                    await async_api.async_connect()
                return ctx.exception

        async_exc = asyncio.run(run_connect())
        self.assertEqual(async_exc.args, (429, b"Requests are blocked"))
        self.assertEqual(async_exc.retry_after, 60.0)

    def test_bare_429_while_retry_in_flight_does_not_escalate_streak(self):
        api = _api()
        api._rate_limit_retry_in_flight = True
        with patch(
            "ariston.ariston_api.requests.request",
            return_value=_sync_response(429, b"Requests are blocked"),
        ):
            with self.assertRaises(ConnectionException) as ctx:
                api._get("https://example/api")
        self.assertEqual(ctx.exception.args, (429, "Requests are blocked"))
        self.assertIsNone(ctx.exception.retry_after)
        self.assertEqual(api._rate_limit_streak, 0)


if __name__ == "__main__":
    unittest.main()
