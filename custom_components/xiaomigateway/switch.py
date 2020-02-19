"""
Add support for Aqara RELAY (LLRZMK11LM)
"""
# Import the device class from the component that you want to support

import homeassistant.helpers.config_validation as cv
import logging
import voluptuous as vol
import asyncio
import datetime

from homeassistant.const import (STATE_OFF, STATE_ON, POWER_WATT)
from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.entity import Entity
from functools import partial
from math import ceil
from . import DOMAIN

# Home Assistant depends on 3rd party packages for API specific code.
REQUIREMENTS = ['python-miio>=0.3.7']

# Load power in watts (W)
ATTR_LOAD_POWER = "load_power"
ATTR_CURRENT_POWER_W = 'current_power_w'
#ATTR_CURRENT_POWER_MWH = 'current_power_w'

# Total (lifetime) power consumption in watts
ATTR_POWER = "power"
ATTR_POWER_CONSUMED = "power_consumed"
#ATTR_IN_USE = "in_use"

_LOGGER = logging.getLogger(__name__)

#LOAD_POWER = "load_power"
#POWER_CONSUMED = "power_consumed"
#ENERGY_CONSUMED = "energy_consumed"
#IN_USE = "inuse"

POWER=0.0


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Setup the Aqra LED Bulb."""

    if DOMAIN not in hass.data:
        return False

    devices=[]
    i = 0
#    device = hass.data[DOMAIN]['device']
    for sid in hass.data[DOMAIN]['switch']['sid']:
        name = hass.data[DOMAIN]['switch']['name'][i]
        device = hass.data[DOMAIN]['switch']['device'][i]
        if sid not in hass.data[DOMAIN]['power']:
            hass.data[DOMAIN]['power'][sid]={"power":None,"yesterday":None,"power_consum":None}
        w_sensor=XiaomiGatewaySensorW(hass.data[DOMAIN]['power'][sid],device, name + '.power', sid)
        devices.append(w_sensor)
        devices.append(XiaomiGatewaySwitch(hass.data[DOMAIN]['power'][sid],device, name, sid, 'channel_0', w_sensor))
        devices.append(XiaomiGatewaySwitch(hass.data[DOMAIN]['power'][sid],device, name, sid, 'channel_1', w_sensor))
        devices.append(XiaomiGatewayLight(device, name, sid))
        i = i + 1
    if len(devices) > 0:
        async_add_devices(devices, update_before_add=True)
    return True

class XiaomiGatewaySwitch(SwitchDevice):
    """Representation of a XiaomiPlug."""

    def __init__(self, data, device, name, sid, channel, w_sensor):
        """Initialize the XiaomiPlug."""
        self._data = data
        self._state = None
        self._device = device
        self._sid = sid
        self._channel = channel
        self._name = name
        self._w_sensor = None
        if w_sensor is not None:
            self._w_sensor = w_sensor
        self._power = None
        self._power_consumed = None
        self._supports_power_consumption = True
# supports_power_consumption
        _LOGGER.info("Start Aqara Relay name: %s sid: %s",self._name, self._sid)

    async def _try_command(self, func, *args, **kwargs):
        """Call a device command handling error messages."""
        from miio import DeviceException
        try:
            result = await self.hass.async_add_job(
                partial(func, *args, **kwargs))
            return result
        except DeviceException as exc:
            _LOGGER.error("Error send command %s",args,exc)
            return []

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
#            return "mdi:power-plug"
        return "mdi:power-socket"

    @property
    def name(self):
        """Return the icon to use in the frontend, if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if it is on."""
        if self._state:
            return True
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
#        if self._supports_power_consumption:
        attrs = {
#            ATTR_IN_USE: self._in_use,
            ATTR_LOAD_POWER: self._power,
            ATTR_POWER: self._power,
            ATTR_CURRENT_POWER_W: self._power,
            ATTR_POWER_CONSUMED: self._power_consumed,
        }
        return attrs

    @property
    def should_poll(self):
        """Return the polling state. Polling needed for Zigbee plug only."""
        return self._supports_power_consumption

    @property
    def current_power_w(self):
        return self._power

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        result = await self._try_command(
            self._device.send,
            'toggle_ctrl_neutral', [self._channel,'on'],self._sid)
        if result[0] == "ok":
            self._state = True
            self.async_schedule_update_ha_state()

    async def async_toggle(self, **kwargs):
        """Turn the switch on."""
        if self._state is not None:
            toggle = self._state
            result = await self._try_command(
                self._device.send,
                'toggle_ctrl_neutral', [self._channel,'toggle'],self._sid)
            if result[0] == "ok"
                if toggle:
                    self._state = False
                else:
                    self._state = True
                self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        result = await self._try_command(
            self._device.send,
            'toggle_ctrl_neutral', [self._channel,'off'],self._sid)
        if result[0] == "ok":
            self._state = False
            self.async_schedule_update_ha_state()

    async def async_update(self):
        """Get data from hub."""
        from miio import DeviceException
        try:
            result = await self._try_command(
                self._device.send,
                'get_device_prop_exp',[[self._sid, self._channel]])
            if result[0] is not None:
                if result[0][0] == 'on':
                    self._state=True
                elif result[0][0] == 'off':
                    self._state=False
            if self._w_sensor is not None:
                await self._w_sensor.async_update()
                self._power = self._w_sensor.state
                self._power_consumed = self._data['power_consum']

            _LOGGER.debug("Switch POWER %.2f %.2f",self._power, self._power_consumed)

        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)

class XiaomiGatewaySensorW(Entity):
    """Representation of a POWER sensor."""

    def __init__(self,data,device, name, sid):
        """Initialize the sensor."""
        self._data = data
        self._state = None
        self._device = device
        self._sid = sid
        self._name = name
        self._data['power'] = 0.0
        self._data['yesterday'] = datetime.datetime.now()
        self._data['power_consum'] = 0.0

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def GetState(self):
        """Return the state of the sensor."""
        return str(self._state)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return POWER_WATT

    async def async_update(self):
        """
        Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        from miio import DeviceException

        try:
            result = await self.hass.async_add_job(
                partial(self._device.send, 'get_device_prop_exp', [[self._sid, "load_power"]]))
            if result[0] is not None:
                self._state=result[0][0]
                today = datetime.datetime.now()
                delta = today - self._data['yesterday']
                self._data['power_consum'] = round((self._data['power_consum'] + float(self._data['power']*delta.seconds/3600)),2)
                self._data['power'] = self._state
                self._data['yesterday'] = today
                POWER=self._state
                _LOGGER.debug("Sensor POWER %.2f",POWER)
        except DeviceException as ex:
            _LOGGER.error("Got exception while fetching the state", ex)

