"""Config flow for Metlink departure info."""
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
from typing import Any, Dict, Optional
from aiohttp import ClientResponseError
from homeassistant import config_entries, core
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_STOP_ID,
    CONF_ROUTE,
    CONF_DEST,
    CONF_NUM_DEPARTURES,
    CONF_STOPS,
)
from .MetlinkAPI import Metlink

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): cv.string})
STOP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID): vol.All(cv.string, vol.Length(min=4, max=4)),
        vol.Optional(CONF_ROUTE, default=""): vol.All(cv.string, vol.Length(max=3)),
        vol.Optional(CONF_DEST, default=""): cv.string,
        vol.Optional(CONF_NUM_DEPARTURES, default=1): cv.positive_int,
        vol.Optional("add_another", default=False): cv.boolean,
    }
)


async def validate_auth(apikey: str, hass: core.HomeAssistant) -> None:
    """Validate a Metlink API key.

    Raises a ValueError if the api key is invalid.
    """
    session = async_get_clientsession(hass)
    metlink = Metlink(session, apikey)

    try:
        await metlink.get_predictions("9999")
    except ClientResponseError:
        raise ValueError


class MetlinkNZConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Metlink config flow."""

    async def async_step_user(self, user_input: Dict[str, Any] = None):
        """Invoked when a user initiates a flow from the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate that the api key is valid.
            try:
                await validate_auth(user_input[CONF_API_KEY], self.hass)
            except ValueError:
                errors["base"] = "auth"

            if not errors:
                self.data = user_input
                self.data[CONF_STOPS] = []
                # Return the form for the next step
                return await self.async_step_stop()

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_stop(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a stop to watch."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data[CONF_STOPS].append(
                {
                    CONF_STOP_ID: user_input[CONF_STOP_ID],
                    CONF_ROUTE: user_input.get(CONF_ROUTE),
                    CONF_DEST: user_input.get(CONF_DEST),
                    CONF_NUM_DEPARTURES: user_input.get(CONF_NUM_DEPARTURES, 1),
                }
            )
            # show the form again if add_another is ticked
            if user_input.get("add_another", False):
                return await self.async_step_stop()

            # User is done adding stops, now create the config entry
            return self.async_create_entry(title="Metlink NZ", data=self.data)

        return self.async_show_form(
            step_id="stop", data_schema=STOP_SCHEMA, errors=errors
        )
