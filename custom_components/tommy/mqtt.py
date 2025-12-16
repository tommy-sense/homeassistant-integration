"""MQTT client for TOMMY communication."""

import asyncio
import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client for communicating with TOMMY."""

    def __init__(self, host: str, port: int = 1886) -> None:
        """
        Initialize the MQTT client.

        Args:
            host: The MQTT broker host.
            port: The MQTT broker port (default 1886).

        """
        self.host = host
        self.port = port

        self._client: mqtt.Client | None = None
        self._connected = False
        self._event_handlers: dict[str, list[Callable]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def on(self, topic: str, handler: Callable) -> None:
        """
        Register a topic handler.

        Args:
            topic: The MQTT topic to listen for.
            handler: The callback function to call when a message is received.

        """
        if topic not in self._event_handlers:
            self._event_handlers[topic] = []
        self._event_handlers[topic].append(handler)

    def off(self, topic: str, handler: Callable) -> None:
        """
        Unregister a topic handler.

        Args:
            topic: The MQTT topic.
            handler: The callback function to remove.

        """
        if topic in self._event_handlers and handler in self._event_handlers[topic]:
            self._event_handlers[topic].remove(handler)

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:  # noqa: ANN001, ARG002
        """Handle MQTT connection event."""
        if rc == 0:
            self._connected = True
            _LOGGER.info("MQTT connected to %s:%s", self.host, self.port)

            # Subscribe to the zone config topic
            client.subscribe("/topic/zone-config")
            _LOGGER.info("Subscribed to /topic/zone-config")

            # Subscribe to the zone state topic
            client.subscribe("/topic/zone-state")
            _LOGGER.info("Subscribed to /topic/zone-state")
        else:
            _LOGGER.error("MQTT connection failed with code %s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:  # noqa: ANN001, ARG002
        """Handle MQTT disconnection event."""
        self._connected = False
        _LOGGER.warning("MQTT disconnected from TOMMY (code: %s)", rc)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:  # noqa: ANN001, ARG002
        """Handle incoming MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            # Try to parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                _LOGGER.warning(
                    "Received non-JSON message on topic %s: %s", topic, payload
                )
                return

            # Call registered handlers for this topic
            if topic in self._event_handlers:
                for handler in self._event_handlers[topic]:
                    try:
                        if self._loop and asyncio.iscoroutinefunction(handler):
                            # Schedule coroutine in the event loop
                            asyncio.run_coroutine_threadsafe(handler(data), self._loop)
                        else:
                            handler(data)
                    except Exception:
                        _LOGGER.exception(
                            "Error in message handler for topic %s", topic
                        )

        except Exception:
            _LOGGER.exception("Error processing MQTT message")

    async def connect(self) -> None:
        """Connect to the MQTT broker."""
        if self._client is not None:
            _LOGGER.warning("MQTT client already connecting/connected")
            return

        self._loop = asyncio.get_event_loop()

        _LOGGER.info("Connecting to TOMMY MQTT broker at %s:%s", self.host, self.port)

        # Create MQTT client with auto-reconnect enabled
        self._client = mqtt.Client(reconnect_on_failure=True)

        # Configure exponential reconnect delay (min 1s, max 120s)
        self._client.reconnect_delay_set(min_delay=1, max_delay=120)

        # Set callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        try:
            # Connect to broker
            self._client.connect(self.host, self.port, 60)

            # Start the network loop in a separate thread
            self._client.loop_start()

            # Wait a bit for connection to establish
            await asyncio.sleep(1)

        except Exception:
            _LOGGER.exception("Error connecting to MQTT broker")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                _LOGGER.exception("Error disconnecting MQTT client")
            self._client = None

        self._connected = False
        self._loop = None
        _LOGGER.info("MQTT connection stopped")

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._connected
