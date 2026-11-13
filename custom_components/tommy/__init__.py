"""TOMMY integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as ha_version
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.loader import async_get_integration

from .api import Api
from .const import CONF_HOST, CONF_MQTT_PORT, DOMAIN
from .zone_manager import TommyZoneManager

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [BINARY_SENSOR_DOMAIN]

# Create config entry
type TommyConfigEntry = ConfigEntry[Api]


async def async_setup_entry(
    hass: HomeAssistant, config_entry: TommyConfigEntry
) -> bool:
    """Set up TOMMY from a config entry."""
    # Initialize API connection parameters
    host = config_entry.data.get(CONF_HOST)
    mqtt_port = config_entry.data.get(CONF_MQTT_PORT)

    # Validate configuration
    if not all([host, mqtt_port]):
        _LOGGER.error(
            "Failed to get configuration: host=%s, mqtt_port=%s",
            host,
            mqtt_port,
        )
        return False

    # Connect to API
    integration = await async_get_integration(hass, DOMAIN)
    hello = {
        "integration": "homeassistant",
        "version": str(integration.version),
        "homeassistantVersion": ha_version,
    }
    api = Api(hass, host, mqtt_port, hello)
    try:
        await api.connect()
    except OSError as err:
        raise ConfigEntryNotReady(
            f"Cannot reach TOMMY MQTT broker at {host}:{mqtt_port}: {err}"
        ) from err

    # Create or get the hub device first
    device_registry = dr.async_get(hass)
    hub = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="TOMMY Hub",
    )

    # Create zone manager to handle entity lifecycle
    zone_manager = TommyZoneManager(hass, config_entry, hub.id)

    config_entry.runtime_data = api

    # Store zone manager in hass.data for access by platforms
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "zone_manager": zone_manager,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Start API
    await api.start(
        on_zone_config_update=zone_manager.on_zone_config_update,
        on_zone_motion_update=zone_manager.on_zone_motion_update,
        on_connection_change=zone_manager.on_connection_change,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: TommyConfigEntry) -> bool:
    """Unload a config entry."""
    api = entry.runtime_data

    # Stop API
    await api.stop()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up stored data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
