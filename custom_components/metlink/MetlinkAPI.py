"""Interface to the metlink web service."""
# Copyright 2021 Jason Rumney
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from datetime import timedelta
import logging

from aiohttp import ClientResponseError
from homeassistant.const import CONTENT_TYPE_JSON
import homeassistant.util.dt as dt_util

BASE_URL = "https://api.opendata.metlink.org.nz/v1"
PREDICTIONS_URL = BASE_URL + "/stop-predictions"
SERVICE_ALERTS_URL = BASE_URL + "/gtfs-rt/servicealerts"
STOP_PARAM = "stop_id"
APIKEY_HEADER = "X-Api-Key"

# Service alerts cover the whole network, so one response serves every stop.
ALERTS_CACHE_TIME = timedelta(seconds=60)
# Back-off used when the server asks us to slow down without saying how long.
DEFAULT_BACKOFF = timedelta(minutes=5)
MAX_BACKOFF = timedelta(hours=1)
# HTTP statuses that mean "try again later" rather than "your request is wrong".
RETRY_STATUSES = (429, 500, 502, 503, 504)

_LOGGER = logging.getLogger(__name__)


class MetlinkRateLimited(Exception):
    """The API asked us to back off, or we are still backing off."""

    def __init__(self, retry_at):
        super().__init__(f"Metlink API backing off until {retry_at}")
        self.retry_at = retry_at


def _retry_after(response) -> timedelta:
    """Delay requested by a Retry-After header (seconds form), or the default."""
    value = response.headers.get("Retry-After") if response.headers else None
    try:
        delay = timedelta(seconds=int(value))
    except (TypeError, ValueError):
        return DEFAULT_BACKOFF
    return min(max(delay, timedelta(seconds=1)), MAX_BACKOFF)


class Metlink(object):
    def __init__(self, session, apikey):
        """
        interface to Metlink API.

        Args:
          apikey (str) : The API key registered at opendata.metlink.org.nz
        """
        self._session = session
        self._key = apikey
        # One client is shared by all the sensors of a config entry.
        self._alerts = None
        self._alerts_time = None
        self._alerts_lock = asyncio.Lock()
        self.retry_at = None

    def _check_backoff(self):
        if self.retry_at is not None and dt_util.utcnow() < self.retry_at:
            raise MetlinkRateLimited(self.retry_at)

    async def _get(self, url, params=None):
        self._check_backoff()
        headers = {"Accept": CONTENT_TYPE_JSON, APIKEY_HEADER: self._key}
        async with self._session.get(url, params=params, headers=headers) as r:
            if r.status in RETRY_STATUSES:
                self.retry_at = dt_util.utcnow() + _retry_after(r)
                _LOGGER.warning(
                    "Metlink API returned %s, pausing requests until %s",
                    r.status,
                    self.retry_at,
                )
                raise MetlinkRateLimited(self.retry_at)
            r.raise_for_status()
            return await r.json()

    async def get_predictions(self, stop_id):
        """Get arrival/departure predictions for the specified stop."""
        _LOGGER.debug(f"Metlink request for {stop_id}")
        return await self._get(PREDICTIONS_URL, params={STOP_PARAM: stop_id})

    async def get_service_alerts(self):
        """Information about unforeseen events affecting routes, stops, or the network.

        The response is cached for ALERTS_CACHE_TIME and concurrent callers share
        a single request.
        """
        async with self._alerts_lock:
            now = dt_util.utcnow()
            if (
                self._alerts is not None
                and now - self._alerts_time < ALERTS_CACHE_TIME
            ):
                return self._alerts
            _LOGGER.debug("Metlink request for service alerts")
            try:
                self._alerts = await self._get(SERVICE_ALERTS_URL)
            except MetlinkRateLimited:
                raise
            except Exception as ex:
                # Keep serving the last good alerts (or none) for one cache
                # period, so sensors waiting on the lock don't each retry.
                _LOGGER.warning("Metlink service alerts unavailable: %s", ex)
                if self._alerts is None:
                    self._alerts = {"entity": []}
            self._alerts_time = now
            return self._alerts
