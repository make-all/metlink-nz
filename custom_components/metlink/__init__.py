"""Metlink Wellington Transport integration."""
import asyncio
import logging

from homeassistant import config_entries, core

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    data = {**entry.data, **entry.options}
    # Register an update listener to refresh when options are updated.
    update_listener = entry.add_update_listener(options_update_listener)
    data["unsub_options_update_listener"] = update_listener
    hass.data[DOMAIN][entry.entry_id] = data

    # Forward the setup to the sensor platform.
    _LOGGER.debug(f"Setting up based on {entry.data}")
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True


async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    _LOGGER.debug("Reloading config after options update")
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading")
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, "sensor")]
        )
    )
    # Remove the listener
    hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()

    # Remove from domain
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    else:
        _LOGGER.warning("Unload failed")

    return unload_ok


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Setup the Metlink component from yaml configuration."""
    _LOGGER.debug("Setting up from YAML config")
    hass.data.setdefault(DOMAIN, {})
    return True
