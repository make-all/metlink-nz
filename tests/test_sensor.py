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
from pytest_homeassistant_custom_component.common import MockConfigEntry
from aiohttp import ClientResponseError
import homeassistant.util.dt as dt_util

from custom_components.metlink.const import DOMAIN
from custom_components.metlink.sensor import MetlinkSensor, slug


async def test_sensor(hass):
    """Test the sensor initialisation."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"apikey": "dummy", "stops": [{"stop_id": "1111"}]}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_async_update_success(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(
        side_effect=[
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
                        "delay": "PT0S",
                        "vehicle_id": None,
                        "name": "WgtnStn",
                        "arrival": {"expected": None},
                        "departure": {
                            "aimed": "2021-04-29T22:15:00+12:00",
                            "expected": None,
                        },
                        "status": None,
                        "monitored": False,
                        "wheelchair_accessible": False,
                    },
                ],
            }
        ]
    )
    sensor = MetlinkSensor(
        metlink, {"stop_id": "WELL", "route": "KPL", "destination": "Porirua",},
    )
    await sensor.async_update()

    expected = {
        "stop_id": "WELL",
        "departure": "2021-04-29T21:55:00+12:00",
        "description": "KPL Porirua",
        "service_id": "KPL",
        "service_name": "WgtnStn",
        "status": "sched",
        "destination_id": "PORI",
        "destination": "Porirua",
    }

    assert expected == sensor.attrs
    assert expected == sensor.device_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL_dPorirua"
    assert sensor.unit_of_measurement == "min"
    time = dt_util.parse_datetime(expected["departure"])
    minutes = int((time - dt_util.now()).total_seconds() // 60)
    assert sensor.state == minutes


async def test_async_update_failed():
    """Tests a failed async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(
        side_effect=ClientResponseError(request_info="dummy", history="")
    )

    sensor = MetlinkSensor(metlink, {"stop_id": "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"stop_id": "WELL"} == sensor.attrs


def test_slug():
    """Test the slug function"""
    assert "abc_def" == slug("abc def")
    assert "_abc_def_ghi" == slug(" abc'def?ghi")
