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
from custom_components.metlink.sensor import MetlinkSensor, slug

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
                    "aimed": "2021-04-29T21:35:00+12:00",
                    "expected": "2021-04-29T21:37:00+12:00",
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
                    "aimed": "2021-04-29T21:44:00+12:00",
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
                    "aimed": "2021-04-29T21:55:00+12:00",
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
                    "aimed": "2021-04-29T22:15:00+12:00",
                    "expected": "2021-04-29T22:45:34+12:00",
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
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL", CONF_DEST: "Porirua"},
    )
    await sensor.async_update()

    expected = {
        "attribution": ATTRIBUTION,
        "stop_id": "WELL",
        "departure": "2021-04-29T21:55:00+12:00",
        "description": "KPL Porirua",
        "service_id": "KPL",
        "stop_name": "WgtnStn",
        "status": "sched",
        "destination_id": "PORI",
        "destination": "Porirua",
        "delay": 0,
        "wheelchair_accessible": False,
    }

    assert expected == sensor.attrs
    assert expected == sensor.device_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL_dPorirua"
    assert sensor.state == expected["departure"]


async def test_async_update_failed():
    """Tests a failed async_update."""
    metlink = MagicMock()
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
    metlink.get_predictions = AsyncMock(side_effect=TypeError("Test error handling"))

    sensor = MetlinkSensor(metlink, {"stop_id": "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"attribution": ATTRIBUTION, "stop_id": "WELL"} == sensor.attrs


async def test_async_update_multiple(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 4},
    )
    await sensor.async_update()

    expected = {
        "attribution": ATTRIBUTION,
        "stop_id": "WELL",
        "departure": "2021-04-29T21:44:00+12:00",
        "description": "KPL WAIK-All stops",
        "service_id": "KPL",
        "stop_name": "WgtnStn",
        "status": "sched",
        "destination_id": "WAIK",
        "destination": "WAIK-All stops",
        "delay": 0,
        "wheelchair_accessible": False,
        "departure_2": "2021-04-29T21:55:00+12:00",
        "description_2": "KPL Porirua",
        "service_id_2": "KPL",
        "status_2": "sched",
        "destination_id_2": "PORI",
        "destination_2": "Porirua",
        "delay_2": 0,
        "wheelchair_accessible_2": False,
        "departure_3": "2021-04-29T22:45:34+12:00",
        "description_3": "KPL Porirua",
        "service_id_3": "KPL",
        "status_3": "late",
        "destination_id_3": "PORI",
        "destination_3": "Porirua",
        "delay_3": 30,
        "wheelchair_accessible_3": False,
    }

    assert expected == sensor.attrs
    assert expected == sensor.device_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL"
    assert sensor.state == expected["departure"]


def test_slug():
    """Test the slug function"""
    assert "abc_def" == slug("abc def")
    assert "_abc_def_ghi" == slug(" abc'def?ghi")
