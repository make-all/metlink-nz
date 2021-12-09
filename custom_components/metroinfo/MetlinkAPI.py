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

import logging

from homeassistant.const import CONTENT_TYPE_JSON

BASE_URL = "https://apis.metroinfo.co.nz/rti/siri/v1/sm?stopcode="
STOP_CODE = "stop_code"
APIKEY_HEADER = "X-Api-Key"

_LOGGER = logging.getLogger(__name__)


class Metlink(object):
    def __init__(self, session, apikey):
        """
        interface to Metlink API.

        Args:
          apikey (str) : The API key registered at https://apidevelopers.metroinfo.co.nz
        """
        self._session = session
        self._key = apikey

    async def get_predictions(self, stop_id):
        """Get arrival/departure predictions for the specified stop."""
        headers = {"Accept": CONTENT_TYPE_JSON, APIKEY_HEADER: self._key}
        query = {STOP_PARAM: stop_code}
        _LOGGER.debug(f"Metlink request for {stop_id}")
        async with self._session.get(
            PREDICTIONS_URL,
            params=query,
            headers=headers,
        ) as r:
            r.raise_for_status()
            return await r.json()
