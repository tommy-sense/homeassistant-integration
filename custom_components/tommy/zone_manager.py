"""Zone manager for TOMMY integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .binary_sensor import TommyZoneMotionSensor
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import ZoneInfo

_LOGGER = logging.getLogger(__name__)


class TommyZoneManager:
    """Manages TOMMY zone entities and devices."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the zone manager."""
        self.hass = hass
        self.config_entry = config_entry
        self.zones: dict[str, TommyZoneMotionSensor] = {}
        self.zone_info: dict[str, ZoneInfo] = {}
        self.async_add_entities: AddEntitiesCallback | None = None

    async def _create_entities_for_zones(self, zones: list[ZoneInfo]) -> None:
        """Create entities for new zones."""
        if not self.async_add_entities:
            _LOGGER.warning("Cannot create entities - async_add_entities not available")
            return

        new_entities = []
        for zone in zones:
            if zone["id"] not in self.zones:
                entity = TommyZoneMotionSensor(self.config_entry, zone)
                new_entities.append(entity)
                self.zones[zone["id"]] = entity

        if new_entities:
            self.async_add_entities(new_entities)
            _LOGGER.info("Created %d new zone entities", len(new_entities))

    async def _remove_entities_for_zones(self, zone_ids: list[str]) -> None:
        """Remove entities and devices for deleted zones."""
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        # Get all devices for this config entry
        devices = dr.async_entries_for_config_entry(
            device_registry, self.config_entry.entry_id
        )
        device_id_by_zone_id: dict[str, str] = {}

        for device in devices:
            for identifier in device.identifiers:
                if identifier[0] == DOMAIN:
                    identifier_value = identifier[1]
                    # Skip hub device
                    if identifier_value == self.config_entry.entry_id:
                        continue
                    # Extract zone_id from identifier
                    prefix = f"{self.config_entry.entry_id}_"
                    if identifier_value.startswith(prefix):
                        zone_id = identifier_value[len(prefix) :]
                        device_id_by_zone_id[zone_id] = device.id
                        break

        for zone_id in zone_ids:
            # Remove from our tracking first
            if zone_id in self.zones:
                del self.zones[zone_id]
            if zone_id in self.zone_info:
                del self.zone_info[zone_id]

            # Remove entity
            unique_id = f"{self.config_entry.entry_id}_zone_{zone_id}_motion"
            for entity_id, entity_entry in list(entity_registry.entities.items()):
                if (
                    entity_entry.config_entry_id == self.config_entry.entry_id
                    and entity_entry.unique_id == unique_id
                ):
                    entity_registry.async_remove(entity_id)
                    _LOGGER.info("Removed entity for zone %s", zone_id)
                    break

            # Remove device
            device_id = device_id_by_zone_id.get(zone_id)
            if device_id:
                device_registry.async_remove_device(device_id)
                _LOGGER.info("Removed device for zone %s", zone_id)

    async def _update_zone_name(self, zone: ZoneInfo) -> None:
        """Update device and entity names when zone is renamed."""
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        # Update device name
        device_identifier = (DOMAIN, f"{self.config_entry.entry_id}_{zone['id']}")
        device = device_registry.async_get_device(identifiers={device_identifier})
        expected_device_name = f"TOMMY ({zone['name']})"

        if device and device.name != expected_device_name:
            device_registry.async_update_device(device.id, name=expected_device_name)
            _LOGGER.info(
                "Updated device name for zone %s to %s", zone["id"], zone["name"]
            )

        # Clear entity name if incorrectly set (should be None for translation)
        unique_id = f"{self.config_entry.entry_id}_zone_{zone['id']}_motion"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, unique_id
        )
        if entity_id:
            entity_entry = entity_registry.async_get(entity_id)
            if entity_entry and entity_entry.name is not None:
                entity_registry.async_update_entity(entity_id, name=None)

        # Update tracked entity's zone name
        entity = self.zones.get(zone["id"])
        if entity and hasattr(entity, "_zone_name"):
            entity._zone_name = zone["name"]  # noqa: SLF001
            if (
                hasattr(entity, "_attr_device_info") and entity._attr_device_info  # noqa: SLF001
            ):
                entity._attr_device_info["name"] = expected_device_name  # noqa: SLF001
            if hasattr(entity, "hass") and entity.hass:
                entity.async_write_ha_state()

    async def on_zone_config_update(self, zones: list[ZoneInfo]) -> None:
        """Handle zone config update."""
        new_zone_info = {zone["id"]: zone for zone in zones}
        current_zone_ids = set(new_zone_info.keys())
        existing_zone_ids = set(self.zone_info.keys())

        # Handle new zones
        added_zones = current_zone_ids - existing_zone_ids
        if added_zones:
            await self._create_entities_for_zones(
                [new_zone_info[zone_id] for zone_id in added_zones]
            )

        # Handle removed zones
        removed_zones = existing_zone_ids - current_zone_ids
        if removed_zones:
            await self._remove_entities_for_zones(list(removed_zones))

        # Handle renamed zones (same ID, different name)
        for zone_id in current_zone_ids & existing_zone_ids:
            if new_zone_info[zone_id]["name"] != self.zone_info[zone_id]["name"]:
                await self._update_zone_name(new_zone_info[zone_id])

        # Update our zone info tracking
        self.zone_info = new_zone_info

    async def on_zone_motion_update(self, zone_id: str, *, motion: bool) -> None:
        """Handle zone state update."""
        entity = self.zones.get(zone_id)
        if entity and hasattr(entity, "on_motion_update"):
            entity.on_motion_update(zone_id, motion)
