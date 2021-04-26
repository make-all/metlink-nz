"""Interface to the metlink web service."""

import aiohttp
import asyncio
import logging

from homeassistant.const import CONTENT_TYPE_JSON

BASE_URL = "https://api.opendata.metlink.org.nz/v1"
PREDICTIONS_URL = BASE_URL + "/stop_predictions"
STOP_PARAM = "stop_id"
APIKEY_HEADER = "X-Api-Key"

from .const import PREDICTIONS_URL, STOP_PARAM, APIKEY_HEADER

_LOGGER = logging.getLogger(__name__)


class Metlink(object):
    def __init__(self, session, apikey):
        """
        interface to Metlink API.

        Args:
          apikey (str) : The API key registered at opendata.metlink.org.nz
        """
        self._session = session
        self._key = apikey

    async def get_predictions(self, stop_id):
        """Get arrival/departure predictions for the specified stop."""
        headers = {"Accept": CONTENT_TYPE_JSON, APIKEY_HEADER: self._key}
        query = {STOP_PARAM: stop_id}
        async with self._session.get(
            PREDICTIONS_URL, params=query, headers=headers
        ) as r:
            r.raise_for_status()
            return await r.json()
