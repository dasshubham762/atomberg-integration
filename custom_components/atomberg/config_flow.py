"""Config flow for Atomberg integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import AtombergCloudAPI, CannotConnect, InvalidAuth
from .const import (
    CONF_CONTROL_METHOD,
    CONF_FAN_MODEL,
    CONF_IR_EMITTER_ENTITY,
    CONF_REFRESH_TOKEN,
    CONF_USE_CLOUD_CONTROL,
    DOMAIN,
    ENTRIES,
    FAN_MODEL_NAMES,
    ControlMethod,
    FanModel,
)

_LOGGER = logging.getLogger(__name__)

CLOUD_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_REFRESH_TOKEN): cv.string,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USE_CLOUD_CONTROL, default=False): cv.boolean,
    }
)


async def validate_cloud_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate cloud API input."""
    api_key = data[CONF_API_KEY]
    refresh_token = data[CONF_REFRESH_TOKEN]

    api = AtombergCloudAPI(hass, api_key, refresh_token)
    await api.test_connection()

    title = "Atomberg Integration"
    if hass.data.get(DOMAIN):
        title += f" {len(hass.data[DOMAIN][ENTRIES]) + 1}"

    return {"title": title}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Atomberg."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle the initial step - select control method."""
        if user_input is not None:
            control_method = user_input[CONF_CONTROL_METHOD]
            if control_method == ControlMethod.CLOUD:
                return await self.async_step_cloud()
            return await self.async_step_ir()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONTROL_METHOD): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                ControlMethod.CLOUD.value,
                                ControlMethod.IR.value,
                            ],
                            translation_key=CONF_CONTROL_METHOD,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_cloud(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle cloud API setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_cloud_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        **user_input,
                        CONF_CONTROL_METHOD: ControlMethod.CLOUD,
                    },
                )

        return self.async_show_form(
            step_id="cloud",
            data_schema=CLOUD_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_ir(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle IR setup."""
        try:
            from homeassistant.components.infrared import (
                DOMAIN as INFRARED_DOMAIN,
                async_get_emitters,
            )
        except ImportError:
            return self.async_abort(reason="no_ir_emitters")

        emitter_entity_ids = async_get_emitters(self.hass)
        if not emitter_entity_ids:
            return self.async_abort(reason="no_ir_emitters")

        if user_input is not None:
            entity_id = user_input[CONF_IR_EMITTER_ENTITY]
            fan_model = user_input[CONF_FAN_MODEL]

            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(entity_id)
            entity_name = (
                entry.name or entry.original_name or entity_id if entry else entity_id
            )
            model_name = FAN_MODEL_NAMES.get(fan_model, "Fan")
            title = f"Atomberg {model_name} via {entity_name}"

            await self.async_set_unique_id(f"atomberg_ir_{entity_id}_{fan_model}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=title,
                data={
                    **user_input,
                    CONF_CONTROL_METHOD: ControlMethod.IR,
                },
            )

        return self.async_show_form(
            step_id="ir",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FAN_MODEL): SelectSelector(
                        SelectSelectorConfig(
                            options=[model.value for model in FanModel],
                            translation_key=CONF_FAN_MODEL,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_IR_EMITTER_ENTITY): EntitySelector(
                        EntitySelectorConfig(
                            domain=INFRARED_DOMAIN,
                            include_entities=async_get_emitters(self.hass),
                        )
                    ),
                }
            ),
        )


class OptionsFlowHandler(OptionsFlow):
    """Handle options flow for Atomberg."""

    VERSION = 1

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
