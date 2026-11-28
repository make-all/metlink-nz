"""Tests for the Metlink API client."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

import homeassistant.util.dt as dt_util
import pytest

from custom_components.metlink.MetlinkAPI import (
    DEFAULT_BACKOFF,
    PREDICTIONS_URL,
    SERVICE_ALERTS_URL,
    Metlink,
    MetlinkRateLimited,
)

ALERTS = {"entity": [{"id": "a1"}]}


def _client(aioclient_mock):
    return Metlink(aioclient_mock.create_session(asyncio.get_running_loop()), "key")


async def test_alerts_cached(aioclient_mock):
    """Repeated alert lookups within the cache period make one request."""
    aioclient_mock.get(SERVICE_ALERTS_URL, json=ALERTS)
    client = _client(aioclient_mock)
    assert await client.get_service_alerts() == ALERTS
    assert await client.get_service_alerts() == ALERTS
    assert aioclient_mock.call_count == 1


async def test_alerts_concurrent_share_one_request(aioclient_mock):
    """Concurrent callers (one per stop sensor) share a single request."""
    aioclient_mock.get(SERVICE_ALERTS_URL, json=ALERTS)
    client = _client(aioclient_mock)
    results = await asyncio.gather(*[client.get_service_alerts() for _ in range(5)])
    assert results == [ALERTS] * 5
    assert aioclient_mock.call_count == 1


async def test_alerts_cache_expires(aioclient_mock):
    """Alerts are fetched again once the cache period has passed."""
    aioclient_mock.get(SERVICE_ALERTS_URL, json=ALERTS)
    client = _client(aioclient_mock)
    start = dt_util.utcnow()
    with patch("homeassistant.util.dt.utcnow", return_value=start):
        await client.get_service_alerts()
    with patch(
        "homeassistant.util.dt.utcnow", return_value=start + timedelta(seconds=61)
    ):
        await client.get_service_alerts()
    assert aioclient_mock.call_count == 2


async def test_alerts_failure_not_retried_by_waiters(aioclient_mock):
    """A failed alert fetch serves empty alerts for one period, without retries."""
    aioclient_mock.get(SERVICE_ALERTS_URL, status=400)
    client = _client(aioclient_mock)
    results = await asyncio.gather(*[client.get_service_alerts() for _ in range(3)])
    assert results == [{"entity": []}] * 3
    assert aioclient_mock.call_count == 1


async def test_rate_limit_uses_retry_after(aioclient_mock):
    """HTTP 429 with Retry-After pauses all requests for that long."""
    aioclient_mock.get(PREDICTIONS_URL, status=429, headers={"Retry-After": "120"})
    client = _client(aioclient_mock)
    before = dt_util.utcnow()
    with pytest.raises(MetlinkRateLimited) as err:
        await client.get_predictions("5000")
    delay = err.value.retry_at - before
    assert timedelta(seconds=119) <= delay <= timedelta(seconds=121)

    # While backing off, no request reaches the server, alerts included.
    with pytest.raises(MetlinkRateLimited):
        await client.get_predictions("5000")
    with pytest.raises(MetlinkRateLimited):
        await client.get_service_alerts()
    assert aioclient_mock.call_count == 1


async def test_retry_after_http_date(aioclient_mock):
    """Retry-After may be an HTTP-date instead of a number of seconds."""
    when = dt_util.utcnow().replace(microsecond=0) + timedelta(minutes=30)
    aioclient_mock.get(
        PREDICTIONS_URL,
        status=503,
        headers={"Retry-After": when.strftime("%a, %d %b %Y %H:%M:%S GMT")},
    )
    client = _client(aioclient_mock)
    with pytest.raises(MetlinkRateLimited) as err:
        await client.get_predictions("5000")
    assert abs(err.value.retry_at - when) <= timedelta(seconds=2)


async def test_retry_after_long_delay_kept(aioclient_mock):
    """A server-requested delay longer than an hour is honoured (up to MAX_BACKOFF)."""
    aioclient_mock.get(PREDICTIONS_URL, status=429, headers={"Retry-After": "7200"})
    client = _client(aioclient_mock)
    before = dt_util.utcnow()
    with pytest.raises(MetlinkRateLimited) as err:
        await client.get_predictions("5000")
    assert err.value.retry_at - before >= timedelta(seconds=7199)


async def test_shorter_retry_never_shortens_deadline(aioclient_mock):
    """Two requests already in flight: the one answered last with a shorter Retry-After
    must not shorten the deadline the other one set."""
    client = _client(aioclient_mock)
    far = dt_util.utcnow() + timedelta(minutes=30)
    client.retry_at = far
    client._check_backoff = lambda: (
        None
    )  # this request passed the check before `far` was set
    aioclient_mock.get(PREDICTIONS_URL, status=429, headers={"Retry-After": "10"})
    with pytest.raises(MetlinkRateLimited):
        await client.get_predictions("5000")
    assert client.retry_at == far


async def test_server_error_default_backoff(aioclient_mock):
    """A 503 without Retry-After backs off for the default period."""
    aioclient_mock.get(PREDICTIONS_URL, status=503)
    client = _client(aioclient_mock)
    before = dt_util.utcnow()
    with pytest.raises(MetlinkRateLimited) as err:
        await client.get_predictions("5000")
    assert err.value.retry_at - before >= DEFAULT_BACKOFF - timedelta(seconds=1)


async def test_backoff_ends(aioclient_mock):
    """Requests resume once the back-off period is over."""
    aioclient_mock.get(PREDICTIONS_URL, status=429, headers={"Retry-After": "10"})
    client = _client(aioclient_mock)
    with pytest.raises(MetlinkRateLimited):
        await client.get_predictions("5000")
    aioclient_mock.clear_requests()
    aioclient_mock.get(PREDICTIONS_URL, json={"departures": []})
    with patch(
        "homeassistant.util.dt.utcnow",
        return_value=dt_util.utcnow() + timedelta(seconds=11),
    ):
        assert await client.get_predictions("5000") == {"departures": []}
