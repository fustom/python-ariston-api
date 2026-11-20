"""Tests for shared HTTP 429 cooldowns without real network calls or sleeps."""

import asyncio
from datetime import datetime, timezone
from email.utils import format_datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ariston.ariston_api import AristonAPI, ConnectionException, _retry_after_seconds


PATH = "https://example.test/api"


def response(status, body=b"", retry_after=""):
    return SimpleNamespace(
        status=status,
        status_code=status,
        ok=status < 400,
        content=body,
        headers={"Retry-After": retry_after},
        json=lambda: {"ok": True},
    )


def async_response(status, content=b"", retry_after=""):
    result = response(status, content, retry_after)
    result.content = SimpleNamespace(read=AsyncMock(return_value=content))
    result.content_length = len(content)
    result.json = AsyncMock(return_value={"ok": True})
    return result


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.now = 100
        self.clock = SimpleNamespace(monotonic=lambda: self.now, sleep=Mock())
        self.enterContext(patch("ariston.ariston_api.time", self.clock))
        self.enterContext(patch("ariston.ariston_api._RATE_LIMITS", {}))
        self.api = AristonAPI("user", "pass", PATH)

    def assert_rate_limited(self, call):
        with self.assertRaises(ConnectionException) as error:
            call()
        self.assertEqual(error.exception.args[0], 429)

    def test_honors_longer_hint_and_shares_deadline_only_with_same_account_origin(self):
        http = self.enterContext(patch(
            "ariston.ariston_api.requests.request",
            side_effect=[
                response(429, b"Blocked for 66 seconds", "20"),
                response(200, b"{}"),
                response(200, b"{}"),
                response(200, b"{}"),
            ],
        ))
        self.assert_rate_limited(lambda: self.api._get(PATH))
        http.assert_called_once()
        self.clock.sleep.assert_not_called()

        same_account = AristonAPI("USER", "pass", f"{PATH}/v2")
        self.now = 166
        self.assert_rate_limited(lambda: same_account._get(PATH))
        self.assertEqual(AristonAPI("other", "pass", PATH)._get(PATH), {"ok": True})
        other_origin = AristonAPI("user", "pass", "https://other.test/api")
        self.assertEqual(other_origin._get("https://other.test/api"), {"ok": True})

        self.now = 167
        self.assertEqual(same_account._get(PATH), {"ok": True})
        self.assertEqual(http.call_count, 4)

    def test_fallback_doubles_until_capped_and_success_resets_it(self):
        limited = response(429, b"Too many requests", "invalid")
        http = self.enterContext(patch(
            "ariston.ariston_api.requests.request",
            side_effect=[limited] * 6 + [response(200, b"{}"), limited],
        ))
        for delay in (60, 120, 240, 480, 900, 900):
            self.assert_rate_limited(lambda: self.api._get(PATH))
            self.now += delay - 1
            self.assert_rate_limited(lambda: self.api._get(PATH))
            self.now += 1

        self.assertEqual(self.api._get(PATH), {"ok": True})
        self.assert_rate_limited(lambda: self.api._get(PATH))
        self.assertEqual(self.api._rate_limit.deadline, self.now + 60)
        self.assertEqual(http.call_count, 8)

    def test_retry_after_http_date(self):
        now = datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
        date = datetime(2026, 11, 19, 10, 2, tzinfo=timezone.utc)
        with patch("ariston.ariston_api.datetime", wraps=datetime) as clock:
            clock.now.return_value = now
            self.assertEqual(_retry_after_seconds(format_datetime(date, usegmt=True)), 120)

    def test_server_error_retry_rechecks_cooldown(self):
        peer = AristonAPI("user", "pass", PATH)
        http = self.enterContext(patch(
            "ariston.ariston_api.requests.request",
            side_effect=[response(500), response(429, retry_after="80")],
        ))
        self.clock.sleep.side_effect = lambda _: self.assert_rate_limited(
            lambda: peer._get(PATH)
        )
        self.assert_rate_limited(lambda: self.api._get(PATH))
        self.assertEqual(http.call_count, 2)
        self.assertEqual(self.api._rate_limit.deadline, 180)

    def test_async_429_on_server_error_retry_sets_shared_cooldown(self):
        async def exercise():
            session = AsyncMock()
            session.__aenter__.return_value = session
            session.request.side_effect = [
                async_response(500),
                async_response(429, retry_after="70"),
                async_response(200, b"{}"),
            ]
            with (
                patch("ariston.ariston_api.aiohttp.ClientSession", return_value=session),
                patch("ariston.ariston_api.asyncio.sleep", new=AsyncMock()) as sleep,
            ):
                with self.assertRaises(ConnectionException):
                    await self.api._async_get(PATH)
                with self.assertRaises(ConnectionException):
                    await self.api._async_get(PATH)
                self.assertEqual(session.request.await_count, 2)
                sleep.assert_awaited_once_with(5)
                self.now += 70
                self.assertEqual(await self.api._async_get(PATH), {"ok": True})

        asyncio.run(exercise())

    def test_concurrent_429_responses_do_not_shorten_deadline_or_repeat_warning(self):
        async def exercise():
            entered = asyncio.Event()
            release = asyncio.Event()
            slow = async_response(429, retry_after="10")

            async def read_body():
                entered.set()
                await release.wait()
                return b""

            slow.content.read.side_effect = read_body
            session = AsyncMock()
            session.__aenter__.return_value = session

            async def first_request(*args, **kwargs):
                # Both HTTP requests have started before either publishes a block.
                await entered.wait()
                return async_response(429, retry_after="90")

            async def concurrent_response(*args, **kwargs):
                if session.request.await_count == 1:
                    return await first_request()
                return slow

            session.request.side_effect = concurrent_response
            with (
                patch("ariston.ariston_api.aiohttp.ClientSession", return_value=session),
                self.assertLogs("ariston.ariston_api", level="WARNING") as logs,
            ):
                first = asyncio.create_task(self.api._async_get(PATH))
                second = asyncio.create_task(self.api._async_get(PATH))
                await entered.wait()
                self.assert_rate_limited(lambda: self.api._get(PATH))
                release.set()
                errors = await asyncio.gather(first, second, return_exceptions=True)

            self.assertEqual([error.args[0] for error in errors], [429, 429])
            self.assertEqual(self.api._rate_limit.deadline, 190)
            self.assertEqual(len(logs.output), 1)
            self.assertEqual(session.request.await_count, 2)

        asyncio.run(exercise())
