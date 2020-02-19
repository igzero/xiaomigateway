"""
Add support for Aqara light Bulb (ZNLDP12LM)
"""
import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
import asyncio

from homeassistant.components.light import (
    ATTR_OPERATION_MODE,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_ENTITY_ID,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP,
    Light,
)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_TOKEN, STATE_OFF, STATE_ON)
from homeassistant.helpers.entity import Entity
from functools import partial
from math import ceil
from . import DOMAIN

REQUIREMENTS = ['python-miio>=0.3.7']

CCT_MIN = 153
CCT_MAX = 500

"""
Mired calculated https://www.leefilters.com/lighting/mired-shift-calculator.html
"""
MIRED_MIN = 130 # 2700K Min
MIRED_MAX = 351 # 6500K Max

_LOGGER = logging.getLogger(__name__)

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Setup the Aqra LED Bulb."""

    if DOMAIN not in hass.data:
        return False

    devices=[]
    i = 0
#    device = hass.data[DOMAIN]['device']
    for sid in hass.data[DOMAIN]['light']['sid']:
        name = hass.data[DOMAIN]['light']['name'][i]
        device = hass.data[DOMAIN]['light']['device'][i]
        devices.append(XiaomiGatewayLight(device, name, sid))
        i = i + 1
    if len(devices) > 0:
        async_add_devices(devices, update_before_add=True)
    return True

class XiaomiGatewayLight(Light):
    """Representation of Xiaomi Gateway Light."""

    def __init__(self, device, name, sid):
        """Initialize an Aqara LED Bulb."""
        self._device = device
        self._name = name
        self._sid = sid
        self._state = False
        self._brightness = None
        self._color_temp = None
        _LOGGER.info("Start Aqara LED Bulb name: %s sid: %s",self._name, self._sid)

    async def _try_command(self, func, *args, **kwargs):
        """Call a device command handling error messages."""
        from miio import DeviceException
        try:
            result = []
            result = await self.hass.async_add_job(
                partial(func, *args, **kwargs))
            return result
        except DeviceException as exc:
            _LOGGER.error("Error exec %s", args, exc)
            return []

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light.
        self._brightness = int(device.send("get_bright",None,self._sid))
        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def color_temp(self):
        """Return current color temperature, if applicable."""
        return self._color_temp

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self):
        """Return the supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        if ATTR_OPERATION_MODE in kwargs:
            _LOGGER.info("MODE %s",str(kwargs[ATTR_OPERATION_MODE]))

        if self._state == False:
            result = await self._try_command(
                self._device.send,
                'set_power', ['on'],self._sid)
            if result[0] == "ok":
                self._state = True

        if ATTR_COLOR_TEMP in kwargs:
            color_temp = kwargs[ATTR_COLOR_TEMP]
            cct = self.convert(color_temp)
            _LOGGER.debug("CCT %d",cct)
            result = await self._try_command(
                self._device.send,
                'set_ct', [cct],self._sid)
            if result[0] == "ok":
                self._color_temp = color_temp

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            brightness = ceil((brightness * 100) / 255)
            result = await self._try_command(
                self._device.send,
                'set_bright', [brightness],self._sid)
            if result[0] == "ok":
                brightness = 0
                result = await self._try_command(
                    self._device.send,
                    'get_bright', None ,self._sid)
                if result[0] is not None:
                    brightness = result[0]
                    if brightness > 0 and brightness <= 100:
                        self._brightness = ceil((brightness * 255) / 100)
                        self._state = True
                    else:
                        self._state = False
        self.async_schedule_update_ha_state(True)

    async def async_turn_off(self, **kwargsf):
        """Instruct the light to turn off."""
        result = await self._try_command(
            self._device.send,
            'set_power', ['off'],self._sid)
        if result[0] == "ok":
            self._state = False
            self.async_schedule_update_ha_state(True)

    def set_color_temp(self, level, transition=0):
        """Set color temp in kelvin."""
        return self._color_temp

    async def async_update(self):
        """
        Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        brightness = 0
        result = await self._try_command(
            self._device.send,
            'get_bright', None ,self._sid)
        if result[0] is not None:
            brightness = result[0]
            if brightness > 0 and brightness <= 100:
                self._brightness = ceil((brightness * 255) / 100)
                self._state = True
            else:
                self._state = False

    @staticmethod
    def convert(value):
        """ Map value from CCT COLOR_TEMP to Mired """
        mired_span = MIRED_MAX - MIRED_MIN
        percent_span = CCT_MAX - CCT_MIN
        value_scaled = float(value - CCT_MIN) / float(percent_span)
        mired = int(MIRED_MIN + (value_scaled * mired_span))
        _LOGGER.debug("MIRED %d VALUE %d",mired,value)
        return mired
