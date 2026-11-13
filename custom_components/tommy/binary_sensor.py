"""Binary sensor platform for TOMMY integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_HAS_VIA_DEVICE_ID = "via_device_id" in DeviceInfo.__annotations__

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import ZoneInfo

_LOGGER = logging.getLogger(__name__)


def zone_device_info(entry: ConfigEntry, zone_id: str, zone_name: str, hub_device_id: str) -> DeviceInfo:
    """Build the device info for a zone, linked to the TOMMY hub device."""
    if _HAS_VIA_DEVICE_ID:
        via = {"via_device_id": hub_device_id}
    else:
        via = {"via_device": (DOMAIN, entry.entry_id)}
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone_id}")},
        name=f"TOMMY ({zone_name})",
        **via,
    )


MOTION_SENSOR_DESCRIPTION = BinarySensorEntityDescription(
    key="motion",
    device_class=BinarySensorDeviceClass.MOTION,
    translation_key="motion",
)


class TommyZoneMotionSensor(BinarySensorEntity):
    """Representation of a TOMMY zone's motion binary sensor."""

    _attr_has_entity_name = True
    entity_description = MOTION_SENSOR_DESCRIPTION

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneInfo,
        hub_device_id: str,
    ) -> None:
        """Initialize the zone's motion binary sensor."""
        self._entry = entry
        self._hub_device_id = hub_device_id
        self._zone_id = zone["id"]
        self._zone_name = zone["name"]
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone['id']}_motion"
        self._attr_device_info = zone_device_info(entry, zone["id"], zone["name"], hub_device_id)

        # Track last known motion state to avoid unnecessary updates
        # Initialize as None - will be set by first motion update
        self._last_motion_state: bool | None = None

        self._connected = True
        self._zone_available = zone.get("available", True)
        self._attr_available = self._zone_available

    def on_motion_update(self, zone_id: str, motion: bool) -> None:  # noqa: FBT001
        """Handle motion state update API."""
        if zone_id == self._zone_id and self.hass is not None and self._last_motion_state != motion:
            # Only update if state has actually changed
            self._last_motion_state = motion

            # Schedule state update in Home Assistant event loop
            self.async_write_ha_state()

    def set_zone_name(self, zone_name: str) -> None:
        """Track a renamed zone."""
        self._zone_name = zone_name
        self._attr_device_info = zone_device_info(self._entry, self._zone_id, zone_name, self._hub_device_id)

    def set_available(self, *, available: bool) -> None:
        """Update availability when the connection to TOMMY changes."""
        self._connected = available
        self._refresh_available()

    def set_zone_available(self, *, available: bool) -> None:
        """Update availability when TOMMY starts or stops sensing the zone."""
        self._zone_available = available
        self._refresh_available()

    def _refresh_available(self) -> None:
        available = self._connected and self._zone_available
        if self._attr_available == available:
            return
        self._attr_available = available
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Entity has been added to hass."""

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callback when entity is removed."""

    @property
    def zone_id(self) -> str:
        """Return the zone ID."""
        return self._zone_id

    @property
    def zone_name(self) -> str:
        """Return the zone name."""
        return self._zone_name

    @property
    def is_on(self) -> bool | None:
        """Return true if motion is detected in the zone."""
        return self._last_motion_state


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TOMMY binary sensor entities from a config entry."""
    # Get the zone manager from the integration's stored data
    zone_manager = hass.data[DOMAIN][config_entry.entry_id]["zone_manager"]

    # Store the add_entities callback for later use by zone manager
    zone_manager.async_add_entities = async_add_entities
