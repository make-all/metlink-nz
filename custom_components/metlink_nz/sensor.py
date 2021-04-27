"""Sensor platform for Metlink departure info."""
import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional
from aiohttp import ClientError
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_API_KEY, DEVICE_CLASS_TIMESTAMP
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from homeassistant.util.dt import parse_datetime, as_timestamp

from .const import (
    ATTR_AIMED,
    ATTR_DEPARTURE,
    ATTR_DEPARTURES,
    ATTR_DESTINATION,
    ATTR_EXPECTED,
    ATTR_NAME,
    ATTR_OPERATOR,
    ATTR_SERVICE,
    ATTR_SERVICE_NAME,
    ATTR_STATUS,
    ATTR_STOP,
    CONF_DEST,
    CONF_NUM_DEPARTURES,
    CONF_ROUTE,
    CONF_STOPS,
    CONF_STOP_ID,
)
from .MetlinkAPI import Metlink

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=2)

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


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    metlink = Metlink(session, config[CONF_API_KEY])
    sensors = [MetlinkSensor(metlink, stop) for stop in config[CONF_STOPS]]
    async_add_entities(sensors, update_before_add=True)


class MetlinkSensor(Entity):
    """Representation of a Metlink Stop sensor."""

    def __init__(self, metlink: Metlink, stop: Dict[str, str]):
        super().__init__()
        self.metlink = metlink
        self.stop_id = stop[CONF_STOP_ID]
        self.route_filter = stop.get(CONF_ROUTE, None)
        self.dest_filter = stop.get(CONF_DEST, None)
        self.num_departures = stop.get(CONF_NUM_DEPARTURES, 1)
        self.attrs: Dict[str, Any] = {ATTR_STOP: self.stop_id}
        self._name = "Metlink " + self.stop_id
        self._state = None
        self._available = True
        self._icon = DEFAULT_ICON

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique_id of the sensor."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self):
        """Return the icon to use in the frontend based on the operator."""
        return self._icon

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_class(self) -> str:
        return DEVICE_CLASS_TIMESTAMP

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self):
        try:
            data = await self.metlink.get_predictions(self.stop_id)
            num = 0

            for departure in data[ATTR_DEPARTURES]:
                dest = departure[ATTR_DESTINATION].get(ATTR_NAME)
                if self.route_filter is not None:
                    if departure[ATTR_SERVICE] != self.route_filter:
                        continue
                if self.dest_filter is not None:
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
                time = parse_datetime(time)

                if num == 1:
                    # First record is the next departure, so use that
                    # to set the state (departure time) and friendly name
                    # (service id and detination name)
                    self._state = as_timestamp(time)
                    self._icon = OPERATOR_ICONS.get(
                        departure[ATTR_OPERATOR], DEFAULT_ICON
                    )
                    _LOGGER.info(f"{self._name}: departs at {self._state}")
                    suffix = ""
                else:
                    suffix = f"_{num}"
                _LOGGER.debug(f"Parsing {suffix} attributes from {departure}")
                _LOGGER.debug(
                    f"Resolved time as {time} from {departure[ATTR_DEPARTURE][ATTR_AIMED]} and {departure[ATTR_DEPARTURE][ATTR_EXPECTED]}"
                )
                self.attrs[ATTR_DEPARTURE + suffix] = time
                self.attrs[ATTR_SERVICE + suffix] = departure[ATTR_SERVICE]
                self.attrs[ATTR_SERVICE_NAME + suffix] = departure[ATTR_NAME]
                status = departure.get(ATTR_STATUS)
                if status is None:
                    status = DEFAULT_STATUS
                self.attrs[ATTR_STATUS + suffix] = status
                self.attrs[ATTR_DESTINATION + suffix] = dest
                self.attrs[ATTR_STOP + suffix] = departure[ATTR_DESTINATION][ATTR_STOP]
            self._available = True
        except (ClientError):
            self._available = False
            _LOGGER.exception("Error retrieving data from Metlink API")
