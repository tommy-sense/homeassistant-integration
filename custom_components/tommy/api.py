"""API for TOMMY communication."""

import logging
from collections.abc import Callable
from typing import TypedDict

from homeassistant.core import HomeAssistant

from .mqtt import MQTTClient

_LOGGER = logging.getLogger(__name__)


class ZoneInfo(TypedDict, total=False):
    """Zone information structure."""

    id: str
    name: str
    available: bool


class Api:
    """API client for communicating with TOMMY."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        mqtt_port: int,
        hello: dict | None = None,
    ) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.host = host
        self.mqtt_port = mqtt_port
        self._hello = hello
        self._mqtt_client: MQTTClient | None = None

    @property
    def connected(self) -> bool:
        """Check if the API is connected (MQTT is connected)."""
        return self._mqtt_client is not None and self._mqtt_client.is_connected

    def authenticate(self) -> None:
        """Authenticate."""

    async def _parse_zone_config(self, data: dict) -> None:
        """Handle zone config events."""
        try:
            if isinstance(data, dict):
                if "zones" in data:
                    zones = data["zones"]
                    await self._on_zone_config_update(zones)
                else:
                    _LOGGER.warning("Received unexpected zone config format: %s", data)
        except Exception:
            _LOGGER.exception("Error processing zone config")

    async def _parse_zone_state(self, data: dict) -> None:
        """Handle zone state events."""
        try:
            if isinstance(data, dict):
                if "zoneId" in data and "motion" in data:
                    zone_id = data["zoneId"]
                    motion = data["motion"]

                    if motion in ("detected", "holding"):
                        motion = True
                    elif motion == "clear":
                        motion = False
                    else:
                        _LOGGER.warning(
                            "Unknown or missing motion state '%s' for zone %s, " "defaulting to False",
                            motion,
                            zone_id,
                        )
                        motion = False

                    await self._on_zone_motion_update(zone_id, motion=motion)
                else:
                    _LOGGER.warning("Received unexpected message format: %s", data)
        except Exception:
            _LOGGER.exception("Error processing zone state")

    async def connect(self) -> None:
        """Connect to the MQTT broker. Raises OSError if TOMMY is unreachable."""
        mqtt_client = MQTTClient(self.host, port=int(self.mqtt_port), hello=self._hello)

        # Register handler for zone config updates
        mqtt_client.on(
            "/topic/zone-config",
            self._parse_zone_config,
        )

        # Register handler for zone state updates
        mqtt_client.on(
            "/topic/zone-state",
            self._parse_zone_state,
        )

        await mqtt_client.connect()
        self._mqtt_client = mqtt_client

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
        on_connection_change: Callable[[bool], None],
    ) -> None:
        """Start the API."""
        # Add callbacks
        self._on_zone_config_update = on_zone_config_update
        self._on_zone_motion_update = on_zone_motion_update

        # Start receiving MQTT push updates
        if self._mqtt_client:
            self._mqtt_client.on_connection_change(on_connection_change)
            await self._mqtt_client.start_loop()

    async def stop(self) -> None:
        """Stop the API."""
        await self._stop_mqtt()
