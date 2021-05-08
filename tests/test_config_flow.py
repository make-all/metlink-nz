"""Tests for the config_flow."""
from unittest.mock import patch, AsyncMock, ANY
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from aiohttp import ClientResponseError

from homeassistant.const import CONF_API_KEY
from custom_components.metlink.const import (
    DOMAIN,
    CONF_STOPS,
    CONF_STOP_ID,
    CONF_ROUTE,
    CONF_DEST,
    CONF_NUM_DEPARTURES,
)
from custom_components.metlink import config_flow


async def test_init(hass):
    """Test the sensor initialisation."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "dummy", CONF_STOPS: [{CONF_STOP_ID: "1111"}]},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.metlink_1111")
    assert state


@patch("custom_components.metlink.config_flow.Metlink")
async def test_validate_auth_valid(m_metlink, hass):
    """Test that no exception is raised for valid auth."""
    m_instance = AsyncMock()
    m_instance.get_predictions = AsyncMock()
    m_metlink.return_value = m_instance
    await config_flow.validate_auth("apikey", hass)


@patch("custom_components.metlink.config_flow.Metlink")
async def test_validate_auth_invalid(m_metlink, hass):
    """Test that ValueError is raised for invalid auth."""
    m_instance = AsyncMock()
    m_instance.get_predictions = AsyncMock(
        side_effect=ClientResponseError(request_info="dummy", history="")
    )
    m_metlink.return_value = m_instance
    with pytest.raises(ValueError):
        await config_flow.validate_auth("apikey", hass)


async def test_flow_user_init(hass):
    """Test the initialisation of the form in the first step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    expected = {
        "data_schema": config_flow.AUTH_SCHEMA,
        "description_placeholders": None,
        "errors": {},
        "flow_id": ANY,
        "handler": "metlink",
        "step_id": "user",
        "type": "form",
        "last_step": ANY,
    }
    assert expected == result


@patch("custom_components.metlink.config_flow.validate_auth")
async def test_flow_user_init_invalid_apikey(m_validate_auth, hass):
    """Test errors populated when apikey is invalid."""
    m_validate_auth.side_effect = ValueError
    _result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_API_KEY: "bad"}
    )
    assert {"base": "auth"} == result["errors"]


@patch("custom_components.metlink.config_flow.validate_auth")
async def test_flow_user_init_data_valid(m_validate_auth, hass):
    """Test we advance to the next step when api key is valid."""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_API_KEY: "dummy"}
    )
    assert "stop" == result["step_id"]
    assert "form" == result["type"]


async def test_flow_stop_init_form(hass):
    """Test the initialisation of the form in the second step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "stop"}
    )
    expected = {
        "data_schema": config_flow.STOP_SCHEMA,
        "description_placeholders": None,
        "errors": {},
        "flow_id": ANY,
        "handler": "metlink",
        "step_id": "stop",
        "type": "form",
        "last_step": ANY,
    }
    assert expected == result


async def test_flow_stop_add_another(hass):
    """Test we show the stop flow again if the add_another box was checked."""
    config_flow.MetlinkNZConfigFlow.data = {
        CONF_API_KEY: "dummy",
        CONF_STOPS: [],
    }
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "stop"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_STOP_ID: "1111", "add_another": True},
    )
    assert "stop" == result["step_id"]
    assert "form" == result["type"]


@patch("custom_components.metlink.config_flow.Metlink")
async def test_flow_stops_creates_config_entry(m_metlink, hass):
    """Test the config entry is successfully created."""
    m_instance = AsyncMock()
    m_instance.get_predictions = AsyncMock()
    m_metlink.return_value = m_instance
    config_flow.MetlinkNZConfigFlow.data = {
        CONF_API_KEY: "dummy",
        CONF_STOPS: [],
    }
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "stop"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_STOP_ID: "1111"},
    )
    expected = {
        "version": 1,
        "type": "create_entry",
        "flow_id": ANY,
        "handler": "metlink",
        "title": "Metlink",
        "description": ANY,
        "description_placeholders": None,
        "result": ANY,
        "data": {
            CONF_API_KEY: "dummy",
            CONF_STOPS: [
                {
                    CONF_STOP_ID: "1111",
                    CONF_ROUTE: "",
                    CONF_DEST: "",
                    CONF_NUM_DEPARTURES: 1,
                }
            ],
        },
    }
    assert expected == result


@patch("custom_components.metlink.sensor.Metlink")
async def test_options_flow_init(m_metlink, hass):
    """Test config flow options."""
    m_instance = AsyncMock()
    m_instance.get_predictions = AsyncMock()
    m_metlink.return_value = m_instance

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="metlink_1111",
        data={CONF_API_KEY: "dummy", CONF_STOPS: [{CONF_STOP_ID: "1111"}]},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert "form" == result["type"]
    assert "init" == result["step_id"]
    assert {} == result["errors"]
    # Verify multi_select options populated with configured repos.
    assert {"sensor.metlink_1111": "Metlink 1111"} == result["data_schema"].schema[
        "stops"
    ].options


@patch("custom_components.metlink.sensor.Metlink")
async def test_options_flow_remove_stop(m_metlink, hass):
    """Test removing a stop from the options config flow."""
    m_instance = AsyncMock()
    m_instance.get_predictions = AsyncMock()
    m_metlink.return_value = m_instance

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="metlink_1111",
        data={CONF_API_KEY: "dummy", CONF_STOPS: [{CONF_STOP_ID: "1111"}]},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    _result = await hass.config_entries.options.async_init(config_entry.entry_id)
    # submit form with options
    result = await hass.config_entries.options.async_configure(
        _result["flow_id"], user_input={CONF_STOPS: []}
    )
    assert "create_entry" == result["type"]
    assert "" == result["title"]
    assert result["result"] is True
    assert {CONF_STOPS: []} == result["data"]


@patch("custom_components.metlink.sensor.Metlink")
@patch("custom_components.metlink.config_flow.Metlink")
async def test_options_flow_add_stop(m_metlink, m_metlink_flow, hass):
    """Test adding a stop in config flow options."""
    m_instance = AsyncMock()
    m_instance.get_predictions = AsyncMock()
    m_metlink.return_value = m_instance
    m_metlink_flow.return_value = m_instance

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="metlink_1111",
        data={CONF_API_KEY: "dummy", CONF_STOPS: [{CONF_STOP_ID: "1111"}]},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    _result = await hass.config_entries.options.async_init(config_entry.entry_id)
    # submit form with new stop
    result = await hass.config_entries.options.async_configure(
        _result["flow_id"],
        user_input={CONF_STOPS: ["sensor.metlink_1111"], "stop_id": "WELL"},
    )
    assert "create_entry" == result["type"]
    assert "" == result["title"]
    assert result["result"] is True
    expected_stops = [
        {CONF_STOP_ID: "1111"},
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "", CONF_DEST: "", CONF_NUM_DEPARTURES: 1},
    ]
    assert {CONF_STOPS: expected_stops} == result["data"]
