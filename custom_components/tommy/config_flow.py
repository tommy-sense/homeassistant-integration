"""Config flow for TOMMY integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

from .const import (
    CONF_HOST,
    CONF_MQTT_PORT,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=""): str,
        vol.Required(CONF_MQTT_PORT, default=1886): vol.Coerce(int),
    }
)


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the configuration step."""
        # Check for in-progress flows and abort them to allow restart
        in_progress_flows = self.hass.config_entries.flow.async_progress()
        for flow in in_progress_flows:
            if flow.get("handler") == DOMAIN and flow.get("flow_id") != self.flow_id:
                # Abort any other in-progress flows for this domain
                await self.hass.config_entries.flow.async_abort(flow["flow_id"])

        # Only allow one hub to be configured
        await self.async_set_unique_id("tommy_hub")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=f"TOMMY ({user_input[CONF_HOST]})", data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
        )
