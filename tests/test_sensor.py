"""Tests for the sensor module."""
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
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientResponseError
import homeassistant.util.dt as dt_util

from custom_components.metlink.const import (
    ATTRIBUTION,
    CONF_DEST,
    CONF_NUM_DEPARTURES,
    CONF_ROUTE,
    CONF_STOP_ID,
)

from custom_components.metlink.MetlinkAPI import MetlinkRateLimited
from custom_components.metlink.sensor import MetlinkSensor, parse_route_filters, slug

TEST_TIMESTAMP1 = (dt_util.utcnow() + timedelta(hours=2)).isoformat(timespec="seconds")
TEST_TIMESTAMP2 = (dt_util.utcnow() + timedelta(hours=2, minutes=5)).isoformat(
    timespec="seconds"
)
TEST_TIMESTAMP3 = (dt_util.utcnow() + timedelta(hours=2, minutes=30)).isoformat(
    timespec="seconds"
)
TEST_TIMESTAMP4 = (dt_util.utcnow() + timedelta(hours=3)).isoformat(timespec="seconds")

TEST_RESPONSE = [
    {
        "farezone": "1",
        "closed": False,
        "departures": [
            {
                "stop_id": "WELL",
                "service_id": "HVL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "UPPE", "name": "UPPE-All stops"},
                "delay": "PT2M",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": TEST_TIMESTAMP1,
                    "expected": TEST_TIMESTAMP1,
                },
                "status": "delay",
                "monitored": False,
                "wheelchair_accessible": False,
            },
            {
                "stop_id": "WELL",
                "service_id": "KPL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "WAIK", "name": "WAIK-All stops"},
                "delay": "PT0S",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": TEST_TIMESTAMP2,
                    "expected": None,
                },
                "status": None,
                "monitored": False,
                "wheelchair_accessible": False,
            },
            {
                "stop_id": "WELL",
                "service_id": "KPL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "PORI", "name": "Porirua"},
                "delay": "PT0S",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": TEST_TIMESTAMP3,
                    "expected": None,
                },
                "status": None,
                "monitored": False,
                "wheelchair_accessible": False,
            },
            {
                "stop_id": "WELL",
                "service_id": "KPL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "PORI", "name": "Porirua"},
                "delay": "PT30M34S",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": TEST_TIMESTAMP4,
                    "expected": TEST_TIMESTAMP4,
                },
                "status": "late",
                "monitored": False,
                "wheelchair_accessible": False,
            },
        ],
    }
]


async def test_async_update_success(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL", CONF_DEST: "Porirua"},
    )
    await sensor.async_update()
    assert sensor.attrs.pop("last_fetched")

    expected = {
        "attribution": ATTRIBUTION,
        "stop_id": "WELL",
        "departure": TEST_TIMESTAMP3,
        "description": "KPL Porirua",
        "service_id": "KPL",
        "stop_name": "WgtnStn",
        "status": "sched",
        "destination_id": "PORI",
        "destination": "Porirua",
        "delay": 0,
        "wheelchair_accessible": False,
        "monitored": False,
        "vehicle_id": None,
        "alert_count": 0,
    }

    assert expected == sensor.attrs
    assert expected == sensor.extra_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL_dPorirua"
    assert sensor.state == dt_util.parse_datetime(expected["departure"])


async def test_async_update_failed():
    """Tests a failed async_update."""
    metlink = MagicMock()
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    metlink.get_predictions = AsyncMock(
        side_effect=ClientResponseError(request_info="dummy", history="")
    )

    sensor = MetlinkSensor(metlink, {"stop_id": "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"attribution": ATTRIBUTION, "stop_id": "WELL"} == sensor.attrs


async def test_async_update_misformatted():
    """Tests a misformatted async_update."""
    metlink = MagicMock()
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    metlink.get_predictions = AsyncMock(side_effect=TypeError("Test error handling"))

    sensor = MetlinkSensor(metlink, {"stop_id": "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"attribution": ATTRIBUTION, "stop_id": "WELL"} == sensor.attrs


async def test_async_update_multiple(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 4},
    )
    await sensor.async_update()
    assert sensor.attrs.pop("last_fetched")

    expected = {
        "attribution": ATTRIBUTION,
        "stop_id": "WELL",
        "departure": TEST_TIMESTAMP2,
        "description": "KPL WAIK-All stops",
        "service_id": "KPL",
        "stop_name": "WgtnStn",
        "status": "sched",
        "destination_id": "WAIK",
        "destination": "WAIK-All stops",
        "delay": 0,
        "wheelchair_accessible": False,
        "monitored": False,
        "vehicle_id": None,
        "alert_count": 0,
        "departure_2": TEST_TIMESTAMP3,
        "description_2": "KPL Porirua",
        "service_id_2": "KPL",
        "status_2": "sched",
        "destination_id_2": "PORI",
        "destination_2": "Porirua",
        "delay_2": 0,
        "wheelchair_accessible_2": False,
        "monitored_2": False,
        "vehicle_id_2": None,
        "alert_count_2": 0,
        "departure_3": TEST_TIMESTAMP4,
        "description_3": "KPL Porirua",
        "service_id_3": "KPL",
        "status_3": "late",
        "destination_id_3": "PORI",
        "destination_3": "Porirua",
        "delay_3": 30,
        "wheelchair_accessible_3": False,
        "monitored_3": False,
        "vehicle_id_3": None,
        "alert_count_3": 0,
    }

    assert expected == sensor.attrs
    assert expected == sensor.extra_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL"
    assert sensor.state == dt_util.parse_datetime(expected["departure"])


async def test_async_update_multiple_route_filter(hass, aioclient_mock):
    """Tests that comma-separated route filters are supported."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: " KPL, HVL ", CONF_NUM_DEPARTURES: 1},
    )
    await sensor.async_update()

    assert sensor.available is True
    assert sensor.attrs["service_id"] == "HVL"
    assert sensor.attrs["description"] == "HVL UPPE-All stops"


def test_parse_route_filters():
    """Test route filter parser for comma-separated values."""
    assert parse_route_filters(None) == set()
    assert parse_route_filters("") == set()
    assert parse_route_filters("KPL") == {"KPL"}
    assert parse_route_filters(" KPL, HVL ,, ") == {"KPL", "HVL"}


def test_slug():
    """Test the slug function"""
    assert "abc_def" == slug("abc def")
    assert "_abc_def_ghi" == slug(" abc'def?ghi")


async def test_rate_limited_sensor_backs_off():
    """A rate-limited sensor makes no request until the back-off ends."""
    retry_at = dt_util.utcnow() + timedelta(minutes=2)
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=MetlinkRateLimited(retry_at))
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(metlink, {CONF_STOP_ID: "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert sensor.retry_at == retry_at
    # A forced update before retry_at must not reach the API, whatever the
    # normal polling schedule says.
    sensor.update_time = sensor.update_time - timedelta(days=1)
    await sensor.async_update()
    assert metlink.get_predictions.call_count == 1


async def test_alerts_failure_keeps_departures(hass, aioclient_mock):
    """Departures are still published when service alerts cannot be fetched."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(side_effect=ValueError("bad alerts"))
    sensor = MetlinkSensor(metlink, {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL"})
    await sensor.async_update()

    assert sensor.available is True
    assert sensor.attrs["departure"] == TEST_TIMESTAMP2
    assert sensor.attrs["alert_count"] == 0


def _with_trips(response, trips):
    """Return a copy of a predictions response with trip ids added in order."""
    data = deepcopy(response)
    for departure, trip in zip(data["departures"], trips):
        if trip is not None:
            departure["trip_id"] = trip
    return data


def _sensor(responses, **stop):
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=responses)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    return MetlinkSensor(metlink, {CONF_STOP_ID: "WELL", **stop})


async def test_trip_id_published_per_slot():
    """Each departure slot publishes the GTFS trip id when the API supplies it."""
    data = _with_trips(TEST_RESPONSE[0], ["T1", "T2", "T3", "T4"])
    sensor = _sensor([data], **{CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 2})
    await sensor.async_update()

    assert sensor.attrs["trip_id"] == "T2"
    assert sensor.attrs["trip_id_2"] == "T3"


async def test_trip_id_removed_when_missing():
    """A slot whose new departure has no trip id must not keep the old one."""
    first = _with_trips(TEST_RESPONSE[0], ["T1", "T2", "T3", "T4"])
    second = _with_trips(TEST_RESPONSE[0], [None, None, None, None])
    sensor = _sensor([first, second], **{CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 2})
    await sensor.async_update()
    sensor.update_time = sensor.update_time - timedelta(days=1)
    await sensor.async_update()

    assert "trip_id" not in sensor.attrs
    assert "trip_id_2" not in sensor.attrs


async def test_unused_slot_fully_cleared():
    """When fewer departures are returned, every attribute of the dropped slot goes."""
    first = _with_trips(TEST_RESPONSE[0], ["T1", "T2", "T3", "T4"])
    second = deepcopy(first)
    second["departures"] = second["departures"][:2]  # only one KPL departure left
    sensor = _sensor([first, second], **{CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 2})
    await sensor.async_update()
    assert "monitored_2" in sensor.attrs
    sensor.update_time = sensor.update_time - timedelta(days=1)
    await sensor.async_update()

    assert sensor.attrs["departure"] == TEST_TIMESTAMP2
    assert not [a for a in sensor.attrs if a.endswith("_2")]


async def test_no_departures_clears_first_slot():
    """With no matching departures the state and the first slot are cleared."""
    first = _with_trips(TEST_RESPONSE[0], ["T1", "T2", "T3", "T4"])
    empty = deepcopy(first)
    empty["departures"] = []
    sensor = _sensor([first, empty], **{CONF_ROUTE: "KPL"})
    await sensor.async_update()
    sensor.update_time = sensor.update_time - timedelta(days=1)
    await sensor.async_update()

    assert sensor.state is None
    for attr in ("departure", "status", "vehicle_id", "monitored", "trip_id"):
        assert attr not in sensor.attrs
    assert sensor.attrs["stop_id"] == "WELL"


async def test_partial_failure_does_not_hold_polling():
    """A response that fails part-way through is retried on the next scan.

    Previously the polling hold was set while parsing the first departure, so a
    failure on a later departure left partial data in place until the hold
    expired (up to an hour).
    """
    broken = deepcopy(TEST_RESPONSE[0])
    del broken["departures"][2]["wheelchair_accessible"]
    sensor = _sensor(
        [broken, TEST_RESPONSE[0]], **{CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 2}
    )
    before = sensor.update_time
    await sensor.async_update()

    assert sensor.available is False
    assert sensor.update_time == before
    assert "last_fetched" not in sensor.attrs

    await sensor.async_update()
    assert sensor.available is True
    assert sensor.attrs["departure_2"] == TEST_TIMESTAMP3
    assert sensor.attrs["last_fetched"]
