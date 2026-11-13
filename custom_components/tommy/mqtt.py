"""MQTT client for TOMMY communication."""

import asyncio
import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)

HELLO_TOPIC = "/topic/integration-hello"


class MQTTClient:
    """MQTT client for communicating with TOMMY."""

    def __init__(self, host: str, port: int = 1886, hello: dict | None = None) -> None:
        """
        Initialize the MQTT client.

        Args:
            host: The MQTT broker host.
            port: The MQTT broker port (default 1886).
            hello: Sent to TOMMY on every connect so it knows this
                integration's version.

        """
        self.host = host
        self.port = port
        self._hello = hello

        self._client: mqtt.Client | None = None
        self._connected = False
        self._event_handlers: dict[str, list[Callable]] = {}
        self._connection_handler: Callable[[bool], None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def on_connection_change(self, handler: Callable[[bool], None] | None) -> None:
        """Register a handler called with the new state on connect and disconnect."""
        self._connection_handler = handler

    def _notify_connection_change(self, connected: bool) -> None:  # noqa: FBT001
        if self._loop and self._connection_handler:
            self._loop.call_soon_threadsafe(self._connection_handler, connected)

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

            if self._hello:
                client.publish(HELLO_TOPIC, json.dumps(self._hello))

            self._notify_connection_change(True)  # noqa: FBT003
        else:
            _LOGGER.error("MQTT connection failed with code %s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:  # noqa: ANN001, ARG002
        """Handle MQTT disconnection event."""
        self._connected = False
        _LOGGER.warning("MQTT disconnected from TOMMY (code: %s)", rc)
        self._notify_connection_change(False)  # noqa: FBT003

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:  # noqa: ANN001, ARG002
        """Handle incoming MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            # Try to parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                _LOGGER.warning("Received non-JSON message on topic %s: %s", topic, payload)
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
                        _LOGGER.exception("Error in message handler for topic %s", topic)

        except Exception:
            _LOGGER.exception("Error processing MQTT message")

    async def connect(self) -> None:
        """Connect to the MQTT broker."""
        if self._client is not None:
            _LOGGER.warning("MQTT client already connecting/connected")
            return

        self._loop = asyncio.get_running_loop()

        _LOGGER.info("Connecting to TOMMY MQTT broker at %s:%s", self.host, self.port)

        # Create MQTT client with auto-reconnect enabled
        client = mqtt.Client(reconnect_on_failure=True)

        # Configure exponential reconnect delay (min 1s, max 120s)
        client.reconnect_delay_set(min_delay=1, max_delay=120)

        # Set callbacks
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        await self._loop.run_in_executor(None, client.connect, self.host, self.port, 60)
        self._client = client

    async def start_loop(self) -> None:
        """Start the network loop so messages start flowing."""
        if self._client is None:
            return

        # Start the network loop in a separate thread
        self._client.loop_start()

        # Wait a bit for connection to establish
        await asyncio.sleep(1)

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        # Entities are being torn down, so a deliberate disconnect must not
        # mark them unavailable.
        self._connection_handler = None
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
