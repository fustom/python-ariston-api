"""Unit tests for the 429 rate-limit handling in ariston.ariston_api."""

import asyncio
import time
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from ariston.ariston_api import (
    AristonAPI,
    ConnectionException,
    _parse_block_seconds,
)


@pytest.fixture(autouse=True)
def _reset_blocked_until():
    """Isolate the class-level block window between tests."""
    AristonAPI._blocked_until = 0.0
    yield
    AristonAPI._blocked_until = 0.0


def _api() -> AristonAPI:
    return AristonAPI("user", "pass")


# ---------------------------------------------------------------------------
# parse helper
# ---------------------------------------------------------------------------


def test_parse_block_seconds():
    assert _parse_block_seconds(b"Requests are blocked for 66 seconds") == 66
    assert _parse_block_seconds(b"Requests are blocked for 5 seconds") == 5
    assert _parse_block_seconds(b"Too many requests") is None


# ---------------------------------------------------------------------------
# sync path (requests)
# ---------------------------------------------------------------------------


def _sync_response(status: int, content: bytes = b"", json_data: Any = None):
    response = MagicMock()
    response.ok = status < 400
    response.status_code = status
    response.content = content
    if json_data is not None:
        response.json.return_value = json_data
    return response


def test_429_parses_wait_seconds():
    responses = [
        _sync_response(429, b"Requests are blocked for 66 seconds"),
        _sync_response(200, b"{}", {"ok": True}),
    ]
    http = MagicMock(side_effect=responses)
    sleeps: list[int] = []
    with patch("ariston.ariston_api.requests.request", http), patch(
        "ariston.ariston_api.time.sleep", side_effect=sleeps.append
    ):
        result = _api()._get("https://example/api")

    assert result == {"ok": True}
    assert http.call_count == 2  # exactly one retry
    assert sleeps == [67]  # parsed 66 + 1s margin
    assert AristonAPI._blocked_until > 0  # block window was set


def test_429_without_parsable_body():
    responses = [
        _sync_response(429, b"Too many requests"),
        _sync_response(200, b"{}", {"ok": True}),
    ]
    http = MagicMock(side_effect=responses)
    sleeps: list[int] = []
    with patch("ariston.ariston_api.requests.request", http), patch(
        "ariston.ariston_api.time.sleep", side_effect=sleeps.append
    ):
        result = _api()._get("https://example/api")

    assert result == {"ok": True}
    assert sleeps == [5]  # documented fallback, same as generic error case
    assert http.call_count == 2


def test_429_twice_raises():
    body = b"Requests are blocked for 10 seconds"
    http = MagicMock(
        side_effect=[_sync_response(429, body), _sync_response(429, body)]
    )
    api = _api()
    with patch("ariston.ariston_api.requests.request", http), patch(
        "ariston.ariston_api.time.sleep"
    ):
        with pytest.raises(ConnectionException):
            api._get("https://example/api")

    assert http.call_count == 2  # one retry, then raise — no infinite loop


def test_blocked_until_short_circuits(monkeypatch):
    monkeypatch.setattr(AristonAPI, "_blocked_until", time.time() + 30)
    http = MagicMock()
    api = _api()
    with patch("ariston.ariston_api.requests.request", http):
        with pytest.raises(ConnectionException):
            api._get("https://example/api")

    http.assert_not_called()  # no network call inside the block window


# ---------------------------------------------------------------------------
# async path (aiohttp)
# ---------------------------------------------------------------------------


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


def test_async_429_parses_and_retries():
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

    assert result == {"ok": True}
    assert len(calls) == 2  # exactly one retry
    assert sleeps == [67]  # parsed 66 + 1s margin


def test_async_blocked_until_short_circuits(monkeypatch):
    monkeypatch.setattr(AristonAPI, "_blocked_until", time.time() + 30)
    calls: list[int] = []
    api = _api()

    async def run() -> None:
        with patch(
            "ariston.ariston_api.aiohttp.ClientSession",
            _fake_session_cls([], calls),
        ):
            with pytest.raises(ConnectionException):
                await api._async_get("https://example/api")

    asyncio.run(run())

    assert calls == []  # no network call inside the block window
