"""Tests for the config_flow."""
from unittest.mock import patch, AsyncMock
import pytest

from aiohttp import ClientResponseError

from homeassistant.const import CONF_API_KEY
from custom_components.metlink.const import DOMAIN
from custom_components.metlink import config_flow


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
