"""Config flow for Brink Flair integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_BAUD_RATE,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    DEFAULT_BAUD_RATE,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    REG_I_ACTIVE_FUNCTION,
    SERIAL_BYTESIZE,
    SERIAL_PARITY,
    SERIAL_STOPBITS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT): str,
        vol.Optional(CONF_BAUD_RATE, default=DEFAULT_BAUD_RATE): vol.In(
            [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        ),
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.All(
            int, vol.Range(min=1, max=247)
        ),
    }
)


class BrinkFlairConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Brink Flair."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._test_connection(
                    user_input[CONF_SERIAL_PORT],
                    user_input[CONF_BAUD_RATE],
                    user_input[CONF_SLAVE_ID],
                )
            except ModbusException:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to device")
                errors["base"] = "unknown"
            else:
                unique_id = (
                    f"{user_input[CONF_SERIAL_PORT]}_{user_input[CONF_SLAVE_ID]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Brink Flair 400 ({user_input[CONF_SERIAL_PORT]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(
        self, serial_port: str, baud_rate: int, slave_id: int
    ) -> None:
        """Open the serial port and read one input register to verify connectivity."""
        client = AsyncModbusSerialClient(
            port=serial_port,
            baudrate=baud_rate,
            bytesize=SERIAL_BYTESIZE,
            parity=SERIAL_PARITY,
            stopbits=SERIAL_STOPBITS,
        )
        await client.connect()
        try:
            result = await client.read_input_registers(
                address=REG_I_ACTIVE_FUNCTION, count=1, device_id=slave_id
            )
            if result.isError():
                raise ModbusException("Device returned error response")
        finally:
            client.close()
