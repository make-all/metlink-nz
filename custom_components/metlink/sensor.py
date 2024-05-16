"""Sensor platform for Metlink departure info."""
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

from datetime import timedelta
import logging
import re
from typing import Any, Callable, Dict, Optional

from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass
from homeassistant.const import ATTR_ATTRIBUTION, CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.util.dt as dt_util
from isodate import parse_duration
import voluptuous as vol

from .MetlinkAPI import Metlink
from .const import (
    ATTR_ACCESSIBLE,
    ATTR_AIMED,
    ATTR_ALERT_CAUSE,
    ATTR_ALERT_COUNT,
    ATTR_ALERT_DESCRIPTION,
    ATTR_ALERT_EFFECT,
    ATTR_ALERT_HEADER,
    ATTR_ALERT_SEVERITY_LEVEL,
    ATTR_ALERT_URL,
    ATTR_ALERT,
    ATTR_CAUSE,
    ATTR_DELAY,
    ATTR_DEPARTURE,
    ATTR_DEPARTURES,
    ATTR_DESCRIPTION_TEXT,
    ATTR_DESCRIPTION,
    ATTR_DESTINATION_ID,
    ATTR_DESTINATION,
    ATTR_EFFECT,
    ATTR_ENTITY,
    ATTR_EXPECTED,
    ATTR_HEADER_TEXT,
    ATTR_INFORMED_ENTITY,
    ATTR_LANGUAGE,
    ATTR_MONITORED,
    ATTR_NAME,
    ATTR_OPERATOR,
    ATTR_SERVICE,
    ATTR_SEVERITY_LEVEL,
    ATTR_STATUS,
    ATTR_STOP_NAME,
    ATTR_STOP,
    ATTR_TEXT,
    ATTR_TRANSLATION,
    ATTR_TRIP_ID,
    ATTR_TRIP,
    ATTR_URL,
    ATTR_VEHICLE,
    ATTRIBUTION,
    CONF_DEST,
    CONF_NUM_DEPARTURES,
    CONF_ROUTE,
    CONF_STOP_ID,
    CONF_STOPS,
    DOMAIN,
    LANG,
)

_LOGGER = logging.getLogger(__name__)
VERBOSE = 1
# Set the scan interval to 30 seconds, to get up to date times as the time approaches.  But polls are dynamically limited by update_time below.
SCAN_INTERVAL = timedelta(seconds=30)

STOP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID): cv.string,
        vol.Optional(CONF_ROUTE): cv.string,
        vol.Optional(CONF_DEST): cv.string,
        vol.Optional(CONF_NUM_DEPARTURES): cv.positive_int,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_STOPS): vol.All(cv.ensure_list, [STOP_SCHEMA]),
    }
)

DEFAULT_ICON = "mdi:bus"
OPERATOR_ICONS = {"RAIL": "mdi:train", "EBYW": "mdi:ferry", "WCCL": "mdi:gondola"}
# By default, status is returned as null.  Follow the behaviour of signs and
# call this "sched", meaning scheduled with no realtime status
DEFAULT_STATUS = "sched"


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.info("Setting up Metlink from ConfigEntry")
    config = hass.data[DOMAIN][config_entry.entry_id]
    # Update to include new stops and remove those that have been deselected
    if config_entry.options:
        _LOGGER.info(f"Updating config from {config_entry.options}")
        config.update(config_entry.options)
    session = async_get_clientsession(hass)
    metlink = Metlink(session, config[CONF_API_KEY])
    sensors = [MetlinkSensor(metlink, stop) for stop in config[CONF_STOPS]]
    async_add_entities(sensors, update_before_add=True)


async def async_setup_platform(
    hass: core.HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.info("Setting up Metlink platform.")
    session = async_get_clientsession(hass)
    metlink = Metlink(session, config[CONF_API_KEY])
    sensors = [MetlinkSensor(metlink, stop) for stop in config[CONF_STOPS]]
    async_add_entities(sensors, update_before_add=True)


def slug(text: str):
    return "_".join(re.split(r'["#$%&+,/:;=?@\[\\\]^`{|}~\'\s]+', text))


def metlink_unique_id(d: Dict):
    uid = "metlink_" + d["stop_id"]
    if "route_filter" in d and d["route_filter"] not in (None, ""):
        uid = uid + "_r" + slug(d["route_filter"])
    if "dest_filter" in d and d["dest_filter"] not in (None, ""):
        uid = uid + "_d" + slug(d["dest_filter"])
    return uid

def get_translation(translations: Dict) -> str:
    for translation in translations.get(ATTR_TRANSLATION, {}):
        if translation.get(ATTR_LANGUAGE) == LANG:
            return translation.get(ATTR_TEXT, "")

    return ""

class MetlinkSensor(Entity):
    """Representation of a Metlink Stop sensor."""

    def __init__(self, metlink: Metlink, stop: Dict[str, str]):
        super().__init__()
        self.metlink = metlink
        self.stop_id = stop[CONF_STOP_ID]
        self.route_filter = stop.get(CONF_ROUTE, None)
        self.dest_filter = stop.get(CONF_DEST, None)
        self.num_departures = stop.get(CONF_NUM_DEPARTURES, 1)
        if self.num_departures < 1:
            self.num_departures = 1
        self.attrs: Dict[str, Any] = {
            ATTR_STOP: self.stop_id,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }
        self._name = "Metlink " + self.stop_id
        self.uid = metlink_unique_id(self.__dict__)
        self._state = None
        self._available = True
        self._icon = DEFAULT_ICON
        self.update_time = dt_util.as_local(dt_util.utcnow())
        _LOGGER.debug(f"Created Metlink sensor {self.uid}.")

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique_id of the sensor."""
        return self.uid

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self):
        """Return the icon to use in the frontend based on the operator."""
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self):
        # Only poll the API if it is time to do so
        now = dt_util.as_local(dt_util.utcnow())
        if self.update_time > now:
            return

        num = 0
        try:
            alerts = await self.metlink.get_service_alerts()
            data = await self.metlink.get_predictions(self.stop_id)

            for departure in data[ATTR_DEPARTURES]:
                dest = departure[ATTR_DESTINATION].get(ATTR_NAME)
                if self.route_filter not in (None, ""):
                    if departure[ATTR_SERVICE] != self.route_filter:
                        continue
                if self.dest_filter not in (None, ""):
                    if (
                        departure[ATTR_DESTINATION][ATTR_STOP] != self.dest_filter
                        and dest != self.dest_filter
                    ):
                        continue
                num = num + 1
                if num > self.num_departures:
                    break
                time = departure[ATTR_DEPARTURE].get(ATTR_EXPECTED)
                if time is None:
                    time = departure[ATTR_DEPARTURE].get(ATTR_AIMED)

                # enumerate the service alerts to find any that are relevant to the trip.
                trip_alerts = []
                if ATTR_TRIP_ID in departure:
                    trip_id = departure[ATTR_TRIP_ID]
                    for entity in alerts[ATTR_ENTITY]:
                        alert = entity[ATTR_ALERT]
                        informed_entities = alert[ATTR_INFORMED_ENTITY]
                        if any(informed_entity.get(ATTR_TRIP, {}).get(ATTR_TRIP_ID) == trip_id for informed_entity in informed_entities):
                            trip_alerts.append(alert)

                name = f"{departure[ATTR_SERVICE]} {dest}"
                if num == 1:
                    # First record is the next departure, so use that
                    # to set the state (departure time)
                    next_departure = dt_util.parse_datetime(time)
                    self._state = next_departure
                    self._icon = OPERATOR_ICONS.get(
                        departure[ATTR_OPERATOR], DEFAULT_ICON
                    )
                    self.attrs[ATTR_STOP_NAME] = departure[ATTR_NAME]
                    _LOGGER.info(f"{self._name}: {name} departs at {time}")
                    suffix = ""
                    # Dynamic polling of the API to get accurate predictions
                    # close to the time, without overloading the server when
                    # there is nothing pending:
                    when = (next_departure - now).total_seconds()
                    # Within 3 minutes, poll next call as well
                    if when < 180:
                        self.update_time = now
                    # Within 15 minutes, poll every two minutes
                    elif when < 900:
                        self.update_time = now + timedelta(minutes=2)
                    # Within an hour, poll every 10 minutes
                    elif when < 3600:
                        self.update_time = now + timedelta(minutes=10)
                    # More than an hour away, don't poll until 1 hour before
                    else:
                        self.update_time = next_departure - timedelta(hours=1)

                    _LOGGER.debug(
                        f"Next departure at {next_departure}, blocking updates until {self.update_time}"
                    )
                else:
                    suffix = f"_{num}"
                _LOGGER.log(
                    VERBOSE,
                    f"{self._name}: Parsing {suffix} attributes from {departure}",
                )
                _LOGGER.log(
                    VERBOSE,
                    f"Resolved time as {time} from {departure[ATTR_DEPARTURE][ATTR_AIMED]} and {departure[ATTR_DEPARTURE][ATTR_EXPECTED]}",
                )
                self.attrs[ATTR_DESCRIPTION + suffix] = name
                self.attrs[ATTR_DEPARTURE + suffix] = time
                self.attrs[ATTR_SERVICE + suffix] = departure[ATTR_SERVICE]
                status = departure.get(ATTR_STATUS)
                if status is None:
                    status = DEFAULT_STATUS
                self.attrs[ATTR_STATUS + suffix] = status
                self.attrs[ATTR_DESTINATION + suffix] = dest
                self.attrs[ATTR_DESTINATION_ID + suffix] = departure[ATTR_DESTINATION][
                    ATTR_STOP
                ]
                self.attrs[ATTR_ACCESSIBLE + suffix] = departure[ATTR_ACCESSIBLE]
                self.attrs[ATTR_DELAY + suffix] = int(
                    parse_duration(departure[ATTR_DELAY]) / timedelta(minutes=1)
                )
                self.attrs[ATTR_MONITORED + suffix] = departure[ATTR_MONITORED]
                self.attrs[ATTR_VEHICLE + suffix] = departure[ATTR_VEHICLE]

                # Trip alerts
                self.attrs[ATTR_ALERT_COUNT + suffix] = len(trip_alerts)
                num_alert = 0
                for alert in trip_alerts:
                    alert_suffix = f"_{num_alert}"

                    self.attrs[ATTR_ALERT_HEADER + suffix + alert_suffix] = get_translation(alert.get(ATTR_HEADER_TEXT, {}))
                    self.attrs[ATTR_ALERT_DESCRIPTION + suffix + alert_suffix] = get_translation(alert.get(ATTR_DESCRIPTION_TEXT, {}))
                    self.attrs[ATTR_ALERT_URL + suffix + alert_suffix] = get_translation(alert.get(ATTR_URL, {}))
                    self.attrs[ATTR_ALERT_CAUSE + suffix + alert_suffix] = alert.get(ATTR_CAUSE, "")
                    self.attrs[ATTR_ALERT_EFFECT + suffix + alert_suffix] = alert.get(ATTR_EFFECT, "")

                    num_alert += 1

                # Clear out old alerts
                to_remove = []
                for alert_prefix in [
                    ATTR_ALERT_HEADER,
                    ATTR_ALERT_DESCRIPTION,
                    ATTR_ALERT_URL,
                    ATTR_ALERT_CAUSE,
                    ATTR_ALERT_EFFECT,
                ]:
                    prefix = f"{alert_prefix}{suffix}_"
                    for attr in self.attrs:
                        if attr.startswith(prefix):
                            try:
                                if int(attr.removeprefix(prefix)) >= len(trip_alerts):
                                    # we have an attribute outside of the range of the current alerts
                                    to_remove.append(attr)
                            except ValueError as ex:
                                pass

                for attr in to_remove:
                    self.attrs.pop(attr)

            self._available = True
            # Clear out the unused slots
            for i in range(num, self.num_departures):
                if i == 0:
                    _LOGGER.warning(f"{self._name}: Clearing due to no departure info")
                    suffix = ""
                    self._state = None
                else:
                    _LOGGER.info(
                        f"{self._name}: Clearing departure info for {i} due to insufficient departure info"
                    )
                    suffix = f"_{i+1}"
                    self.attrs.pop(ATTR_DESCRIPTION + suffix, None)
                    self.attrs.pop(ATTR_DEPARTURE + suffix, None)
                    self.attrs.pop(ATTR_DEPARTURE + suffix, None)
                    self.attrs.pop(ATTR_SERVICE + suffix, None)
                    self.attrs.pop(ATTR_STATUS + suffix, None)
                    self.attrs.pop(ATTR_DESTINATION + suffix, None)
                    self.attrs.pop(ATTR_DESTINATION_ID + suffix, None)
                    self.attrs.pop(ATTR_ACCESSIBLE + suffix, None)
                    self.attrs.pop(ATTR_DELAY + suffix, None)
                    self.attrs.pop(ATTR_ALERT_COUNT + suffix, None)
                    to_remove = []
                    for alert_prefix in [
                        ATTR_ALERT_HEADER,
                        ATTR_ALERT_DESCRIPTION,
                        ATTR_ALERT_URL,
                        ATTR_ALERT_CAUSE,
                        ATTR_ALERT_EFFECT,
                    ]:
                        prefix = f"{alert_prefix}{suffix}"
                        for attr in self.attrs:
                            if attr.startswith(prefix):
                                to_remove.append(attr)

                    for attr in to_remove:
                        self.attrs.pop(attr)

        # set the sensor to unavailable on errors, but leave previous data in
        # attributes, so temporary network issues do not cause glitches.
        except BaseException:
            self._available = False
            _LOGGER.exception(
                "Error retrieving data from Metlink API for sensor %s.", self.name
            )
