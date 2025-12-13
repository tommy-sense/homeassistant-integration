"""Binary sensor platform for TOMMY integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import ZoneInfo

_LOGGER = logging.getLogger(__name__)

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
    ) -> None:
        """Initialize the zone's motion binary sensor."""
        self._zone_id = zone["id"]
        self._zone_name = zone["name"]
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone['id']}_motion"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{zone['id']}")},
            name=f"TOMMY ({zone['name']})",
            via_device=(DOMAIN, entry.entry_id),
        )

        # Track last known motion state to avoid unnecessary updates
        # Initialize as None - will be set by first motion update
        self._last_motion_state: bool | None = None

    def on_motion_update(self, zone_id: str, motion: bool) -> None:  # noqa: FBT001
        """Handle motion state update API."""
        if (
            zone_id == self._zone_id
            and self.hass is not None
            and self._last_motion_state != motion
        ):
            # Only update if state has actually changed
            self._last_motion_state = motion

            # Schedule state update in Home Assistant event loop
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
