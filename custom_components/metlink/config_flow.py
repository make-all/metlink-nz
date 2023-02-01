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

from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from aiohttp import ClientResponseError
from homeassistant import config_entries, core
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get_registry,
)
import voluptuous as vol

from .MetlinkAPI import Metlink
from .const import (
    CONF_DEST,
    CONF_NUM_DEPARTURES,
    CONF_ROUTE,
    CONF_STOP_ID,
    CONF_STOPS,
    DOMAIN,
)
from .sensor import metlink_unique_id

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): cv.string})
STOP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID): vol.All(cv.string, vol.Length(min=3, max=4)),
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
        _LOGGER.error("Metlink API Key rejected by server")
        raise ValueError


class MetlinkNZConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Metlink config flow."""

    async def async_step_user(self, user_input: Dict[str, Any] = None):
        """Invoked when a user initiates a flow from the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate that the api key is valid.
            _LOGGER.debug("Validating user supplied API key.")
            try:
                await validate_auth(user_input[CONF_API_KEY], self.hass)
            except ValueError:
                _LOGGER.warning("API key validation failed, restarting config")
                errors["base"] = "auth"

            if not errors:
                self.data = user_input
                self.data[CONF_STOPS] = []
                # Return the form for the next step
                _LOGGER.info("Proceeding to configure stops")
                return await self.async_step_stop()

        _LOGGER.info("Starting configuration process")
        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_stop(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a stop to watch."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            _LOGGER.info(f"Adding stop {user_input[CONF_STOP_ID]} to config.")
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
                _LOGGER.debug("Continuing to add another stop.")
                return await self.async_step_stop()

            # User is done adding stops, now create the config entry
            n_stops = len(self.data[CONF_STOPS])
            _LOGGER.info(f"Saving config with {n_stops} stops.")
            return self.async_create_entry(title="Metlink", data=self.data)

        _LOGGER.debug("Showing stop configuration form")
        return self.async_show_form(
            step_id="stop", data_schema=STOP_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the component."""
        entity_registry = await async_get_registry(self.hass)
        entries = async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        errors: Dict[str, str] = {}
        all_stops = {e.entity_id: e.original_name for e in entries}
        stop_map = {e.entity_id: e for e in entries}
        # Merge initial config and later modifications
        config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            _LOGGER.debug(f"Starting reconfiguration for {user_input}")
            updated_stops = deepcopy(config.get(CONF_STOPS))
            _LOGGER.debug(f"Stops before reconfiguration: {updated_stops}")

            # Remove unchecked stops.
            removed_entities = [
                entity_id
                for entity_id in stop_map.keys()
                if entity_id not in user_input["stops"]
            ]
            for entity_id in removed_entities:
                # Unregister from HA
                entity_registry.async_remove(entity_id)
                # Remove from our configured stops.
                entry = stop_map[entity_id]
                entry_stop = entry.unique_id
                _LOGGER.info(f"Removing stop {entry_stop}")
                updated_stops = [
                    e for e in updated_stops if metlink_unique_id(e) != entry_stop
                ]

            _LOGGER.debug(f"Stops after removals: {updated_stops}")
            if user_input.get(CONF_STOP_ID):
                updated_stops.append(
                    {
                        CONF_STOP_ID: user_input[CONF_STOP_ID],
                        CONF_ROUTE: user_input.get(CONF_ROUTE),
                        CONF_DEST: user_input.get(CONF_DEST),
                        CONF_NUM_DEPARTURES: user_input.get(CONF_NUM_DEPARTURES, 1),
                    }
                )

            _LOGGER.debug(f"Reconfigured stops: {updated_stops}")
            return self.async_create_entry(
                title="",
                data={CONF_STOPS: updated_stops},
            )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_STOPS, default=list(all_stops.keys())
                ): cv.multi_select(all_stops),
                vol.Optional(CONF_STOP_ID): vol.All(
                    cv.string, vol.Length(min=3, max=4)
                ),
                vol.Optional(CONF_ROUTE, default=""): vol.All(
                    cv.string, vol.Length(max=3)
                ),
                vol.Optional(CONF_DEST, default=""): cv.string,
                vol.Optional(CONF_NUM_DEPARTURES, default=1): cv.positive_int,
            }
        )
        _LOGGER.debug("Showing Reconfiguration form")
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
