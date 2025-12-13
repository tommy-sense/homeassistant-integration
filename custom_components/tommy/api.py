"""API for TOMMY communication."""

import logging
from collections.abc import Callable
from typing import TypedDict

from homeassistant.core import HomeAssistant

from .mqtt import MQTTClient

_LOGGER = logging.getLogger(__name__)


class ZoneInfo(TypedDict):
    """Zone information structure."""

    id: str
    name: str


class Api:
    """API client for communicating with TOMMY."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        mqtt_port: int,
    ) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.host = host
        self.mqtt_port = mqtt_port
        self._mqtt_client: MQTTClient | None = None

    @property
    def connected(self) -> bool:
        """Check if the API is connected (MQTT is connected)."""
        return self._mqtt_client is not None and self._mqtt_client.is_connected

    def authenticate(self) -> None:
        """Authenticate."""

    async def _parse_zone_state(self, data: dict) -> None:
        """Handle zone state events."""
        try:
            if isinstance(data, dict):
                if "zoneId" in data and "motion" in data and "zones" in data:
                    zone_id = data["zoneId"]
                    motion = data["motion"]
                    zones = data["zones"]

                    if motion in ("detected", "holding"):
                        motion = True
                    elif motion == "clear":
                        motion = False
                    else:
                        _LOGGER.warning(
                            "Unknown or missing motion state '%s' for zone %s, "
                            "defaulting to False",
                            motion,
                            zone_id,
                        )
                        motion = False

                    await self._on_zone_config_update(zones)
                    await self._on_zone_motion_update(zone_id, motion=motion)
                else:
                    _LOGGER.warning("Received unexpected message format: %s", data)
        except Exception:
            _LOGGER.exception("Error processing zone state")

    async def _start_mqtt(self) -> None:
        """Start the MQTT connection to receive push updates."""
        self._mqtt_client = MQTTClient(self.host, port=int(self.mqtt_port))

        # Register handler for zone state updates
        self._mqtt_client.on(
            "/topic/zone-state",
            self._parse_zone_state,
        )

        await self._mqtt_client.connect()

    async def _stop_mqtt(self) -> None:
        """Stop the MQTT connection."""
        if self._mqtt_client:
            await self._mqtt_client.disconnect()
            self._mqtt_client = None
        _LOGGER.info("MQTT connection stopped")

    async def start(
        self,
        on_zone_config_update: Callable[[list[ZoneInfo]], None],
        on_zone_motion_update: Callable[[str, bool], None],
    ) -> None:
        """Start the API."""
        # Add callbacks
        self._on_zone_config_update = on_zone_config_update
        self._on_zone_motion_update = on_zone_motion_update

        # Start MQTT
        await self._start_mqtt()

    async def stop(self) -> None:
        """Stop the API."""
        await self._stop_mqtt()
