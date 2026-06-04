"""Support for Template Humidifier."""
import logging

import voluptuous as vol

from homeassistant.components.humidifier import (
    ATTR_HUMIDITY,
    ATTR_MODE,
    DOMAIN as HUMIDIFIER_DOMAIN,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.script import Script
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)

CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_TARGET_HUMIDITY_TEMPLATE = "target_humidity_template"
CONF_CURRENT_HUMIDITY_TEMPLATE = "current_humidity_template"
CONF_STATE_TEMPLATE = "state_template"
CONF_MODE_TEMPLATE = "mode_template"
CONF_ACTION_TEMPLATE = "action_template"
CONF_MODES = "modes"
CONF_SET_TARGET_HUMIDITY_ACTION = "set_target_humidity_action"
CONF_SET_MODE_ACTION = "set_mode_action"
# NEW: turn_on and turn_off actions
CONF_TURN_ON_ACTION = "turn_on_action"
CONF_TURN_OFF_ACTION = "turn_off_action"

DEFAULT_NAME = "Template Humidifier"
DEFAULT_MIN_HUMIDITY = 40
DEFAULT_MAX_HUMIDITY = 70
# Official HA humidifier modes (const.py):
# normal, eco, away, boost, comfort, home, sleep, auto, baby
DEFAULT_MODES = ["normal", "eco", "away", "boost", "comfort", "home", "sleep", "auto", "baby"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_MIN_HUMIDITY, default=DEFAULT_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_MAX_HUMIDITY, default=DEFAULT_MAX_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_TARGET_HUMIDITY_TEMPLATE): cv.template,
        vol.Optional(CONF_CURRENT_HUMIDITY_TEMPLATE): cv.template,
        vol.Optional(CONF_STATE_TEMPLATE): cv.template,
        vol.Optional(CONF_MODE_TEMPLATE): cv.template,
        vol.Optional(CONF_ACTION_TEMPLATE): cv.template,
        vol.Optional(CONF_MODES, default=DEFAULT_MODES): cv.ensure_list,
        vol.Optional(CONF_SET_TARGET_HUMIDITY_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_SET_MODE_ACTION): cv.SCRIPT_SCHEMA,
        # NEW: turn_on and turn_off actions
        vol.Optional(CONF_TURN_ON_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(CONF_TURN_OFF_ACTION): cv.SCRIPT_SCHEMA,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Template Humidifier platform."""
    async_add_entities([TemplateHumidifier(hass, config)])


class TemplateHumidifier(HumidifierEntity):
    """Representation of a Template Humidifier."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
    ) -> None:
        """Initialize the humidifier."""
        self.hass = hass
        self._attr_name = config.get(CONF_NAME)
        self._attr_unique_id = config.get(CONF_UNIQUE_ID)
        self._attr_min_humidity = config.get(CONF_MIN_HUMIDITY)
        self._attr_max_humidity = config.get(CONF_MAX_HUMIDITY)
        self._attr_available_modes = config.get(CONF_MODES)
        
        self._target_humidity_template = config.get(CONF_TARGET_HUMIDITY_TEMPLATE)
        self._current_humidity_template = config.get(CONF_CURRENT_HUMIDITY_TEMPLATE)
        self._state_template = config.get(CONF_STATE_TEMPLATE)
        self._mode_template = config.get(CONF_MODE_TEMPLATE)
        self._action_template = config.get(CONF_ACTION_TEMPLATE)
        
        self._set_target_humidity_script = None
        if CONF_SET_TARGET_HUMIDITY_ACTION in config:
            self._set_target_humidity_script = Script(
                hass, config[CONF_SET_TARGET_HUMIDITY_ACTION], self._attr_name, HUMIDIFIER_DOMAIN
            )
            
        self._set_mode_script = None
        if CONF_SET_MODE_ACTION in config:
            self._set_mode_script = Script(
                hass, config[CONF_SET_MODE_ACTION], self._attr_name, HUMIDIFIER_DOMAIN
            )
        
        # NEW: turn_on and turn_off scripts
        self._turn_on_script = None
        if CONF_TURN_ON_ACTION in config:
            self._turn_on_script = Script(
                hass, config[CONF_TURN_ON_ACTION], self._attr_name, HUMIDIFIER_DOMAIN
            )
            
        self._turn_off_script = None
        if CONF_TURN_OFF_ACTION in config:
            self._turn_off_script = Script(
                hass, config[CONF_TURN_OFF_ACTION], self._attr_name, HUMIDIFIER_DOMAIN
            )

        self._attr_target_humidity = None
        self._attr_current_humidity = None
        self._attr_mode = None
        self._attr_action = None
        self._state = False

        # Set supported features
        self._attr_supported_features = HumidifierEntityFeature(0)
        if self._attr_available_modes:
            self._attr_supported_features |= HumidifierEntityFeature.MODES

        self._attr_device_class = HumidifierDeviceClass.HUMIDIFIER

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._state

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Render templates
        if self._target_humidity_template:
            self._target_humidity_template.hass = self.hass
        if self._current_humidity_template:
            self._current_humidity_template.hass = self.hass
        if self._state_template:
            self._state_template.hass = self.hass
        if self._mode_template:
            self._mode_template.hass = self.hass
        if self._action_template:
            self._action_template.hass = self.hass

        @callback
        def _async_update_state(*_):
            """Update entity state."""
            self._update_state()
            self.async_write_ha_state()

        # Track state changes for all referenced entities
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self._get_template_entities(),
                _async_update_state,
            )
        )

        # Initial update
        self._update_state()

    def _get_template_entities(self) -> list[str]:
        """Get all entities referenced in templates."""
        entities = set()
        for template in [
            self._target_humidity_template,
            self._current_humidity_template,
            self._state_template,
            self._mode_template,
            self._action_template,
        ]:
            if template:
                try:
                    info = template.async_render_to_info()
                    entities.update(info.entities)
                except TemplateError:
                    pass
        return list(entities)

    @callback
    def _update_state(self) -> None:
        """Update entity state from templates."""
        try:
            if self._state_template:
                result = self._state_template.async_render()
                if result in (True, "True", "true", "on", "On", "ON", STATE_ON, 1, "1"):
                    self._state = True
                elif result in (False, "False", "false", "off", "Off", "OFF", STATE_OFF, 0, "0"):
                    self._state = False
                else:
                    self._state = bool(result)
        except TemplateError as ex:
            _LOGGER.error("Error rendering state template: %s", ex)

        try:
            if self._target_humidity_template:
                self._attr_target_humidity = float(
                    self._target_humidity_template.async_render()
                )
        except (TemplateError, ValueError) as ex:
            _LOGGER.error("Error rendering target humidity template: %s", ex)

        try:
            if self._current_humidity_template:
                self._attr_current_humidity = float(
                    self._current_humidity_template.async_render()
                )
        except (TemplateError, ValueError) as ex:
            _LOGGER.error("Error rendering current humidity template: %s", ex)

        try:
            if self._mode_template:
                self._attr_mode = str(self._mode_template.async_render()).strip()
        except TemplateError as ex:
            _LOGGER.error("Error rendering mode template: %s", ex)

        try:
            if self._action_template:
                self._attr_action = str(self._action_template.async_render())
        except TemplateError as ex:
            _LOGGER.error("Error rendering action template: %s", ex)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if self._set_target_humidity_script:
            await self._set_target_humidity_script.async_run(
                {"humidity": humidity}, context=self._context
            )
        else:
            self._attr_target_humidity = humidity
            self.async_write_ha_state()

    async def async_set_mode(self, mode: str) -> None:
        """Set new mode."""
        if self._set_mode_script:
            await self._set_mode_script.async_run(
                {"mode": mode}, context=self._context
            )
        else:
            self._attr_mode = mode
            self.async_write_ha_state()

    # NEW: async_turn_on method
    async def async_turn_on(self, **kwargs) -> None:
        """Turn the humidifier on."""
        if self._turn_on_script:
            await self._turn_on_script.async_run(context=self._context)
        else:
            # Fallback: set state optimistically
            self._state = True
            self.async_write_ha_state()

    # NEW: async_turn_off method
    async def async_turn_off(self, **kwargs) -> None:
        """Turn the humidifier off."""
        if self._turn_off_script:
            await self._turn_off_script.async_run(context=self._context)
        else:
            # Fallback: set state optimistically
            self._state = False
            self.async_write_ha_state()
