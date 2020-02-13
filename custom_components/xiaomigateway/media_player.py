"""
Add support for the Xiaomi Gateway FM Radio.
"""

import homeassistant.helpers.config_validation as cv 
import logging
import voluptuous as vol
import asyncio

from homeassistant.components.media_player import MediaPlayerDevice
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET, SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_SELECT_SOURCE) 
from homeassistant.const import (
    STATE_OFF, STATE_ON)
from homeassistant.helpers.entity import Entity
from functools import partial
from . import DOMAIN

REQUIREMENTS = ['python-miio>=0.3.7']

ATTR_SOURCE = 'source'
ATTR_STATE_PROPERTY = 'state_property'
ATTR_STATE_VALUE = 'state_value'

DEVICE_CLASS_SPEAKER = 'speaker'

_LOGGER = logging.getLogger(__name__)

SUPPORT_XIAOMIGATEWAY_RADIO = \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_VOLUME_MUTE | \
    SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_SET | SUPPORT_NEXT_TRACK | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_SELECT_SOURCE


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Xiaomi Gateway FM Radio miio platform."""

    if DOMAIN not in hass.data:
        return False
    device = hass.data[DOMAIN]['device']
    name = hass.data[DOMAIN]['radio'].get('name')
    source_list = hass.data[DOMAIN]['radio'].get('source_list')
    program_list = hass.data[DOMAIN]['radio'].get('program_list')

    device = XiaomiGatewayRadio(device, name, source_list, program_list)
    async_add_devices([device], update_before_add=True)
    return True

class XiaomiGatewayRadio(MediaPlayerDevice,Entity):
    """Represent the Xiaomi Gateway FM Radio for Home Assistant."""

    def __init__(self, device, name, source_list, program_list):
        """Initialize the entity."""

        self._device = device
        self._name = name
        self._source_list = source_list
        self._program_list = program_list

        self._skip_update = False
        self._icon = 'mdi:radio'
        self._muted = False
        self._volume = None
        self._volume_back = None
        self._available = None
        self._state = None
        self._device_class = DEVICE_CLASS_SPEAKER
        self._state_attrs = {
            ATTR_STATE_PROPERTY: 'pause'
        }
        self._source = None
        self._program = None
        self._url = None
        _LOGGER.info("Start XiaomiGateway FM Radio name: %s",self._name)
    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a device command handling error messages."""
        from miio import DeviceException
        try:
            result = await self.hass.async_add_job(
                partial(func, *args, **kwargs))
            _LOGGER.debug("Response received from Gateway: %s", result)
            return result[0] == "ok"
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    @property
    def device_class(self):
        """Return the display name of this Gateway."""
        return self._device_class

    @property
    def name(self):
        """Return the display name of this Gateway."""
        return self._name

    @property
    def state(self):
        """Return _state variable, containing the appropriate constant."""
        return self._state

    @property
    def assumed_state(self):
        """Indicate that state is assumed."""
        return True

    @property
    def source(self):
        """Return the display name of this Gateway."""
        return self._source

    @property
    def source_list(self):
        """Return the display name of this Gateway."""
        return self._source_list

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_XIAOMIGATEWAY_RADIO

    async def turn_off(self):
        result = await self._try_command(
            "Turning the Gateway off failed.", self._device.send,
            'play_fm', ['off'])
        if result:
            self._state = STATE_OFF
            self.async_schedule_update_ha_state()

    async def turn_on(self):
        """Wake the Gateway back up from sleep."""
        if self._program is not None:
            if self._url is None:
                result = await self._try_command(
                    "Turning the Gateway on failed.", self._device.send,
                    'play_specify_fm', {"id":self._program,"type":0})
            else:
                result = await self._try_command(
                    "Turning the Gateway on failed.", self._device.send,
                    'play_specify_fm', {"id":self._program,"url":self._url,"type":0})
        else:
            result = await self._try_command(
                "Turning the Gateway on failed.", self._device.send,
                'play_fm', ['on'])
        if result:
            self._state = STATE_ON
            self.async_schedule_update_ha_state()

    async def select_source(self,source):
        idx = self._source_list.index(source)
        if idx < len(self._program_list):
            self._program = self._program_list[idx][0]
            if len(self._program_list[idx]) > 1:
                self._url = self._program_list[idx][1]
            else:
                self._url = None
            self._source = source
            if self._url is None:
                result = await self._try_command(
                    "Turning the Gateway on failed.", self._device.send,
                    'play_specify_fm', {"id":self._program,"type":0})
            else:
                    result = await self._try_command(
                        "Turning the Gateway on failed.", self._device.send,
                        'play_specify_fm', {"id":self._program,"url":self._url,"type":0})
            if result:
                self._state = STATE_ON
                self.async_schedule_update_ha_state()
        else:
            self.async_schedule_update_ha_state()


    async def volume_up(self):
        """Increase volume by one."""
        volume = round(self._volume * 100)
        if volume < 100:
            volume = volume + 1
            result = await self._try_command(
                "Turning the Gateway volume failed.", self._device.send,
                'set_fm_volume', [volume])
            if result:
                self.async_schedule_update_ha_state()

    async def volume_down(self):
        """Decrease volume by one."""
        volume = round(self._volume * 100)
        if volume > 0:
            volume = volume - 1
            result = await self._try_command(
                "Turning the Gateway volume failed.", self._device.send,
                'set_fm_volume', [volume])
            if result:
                self.async_schedule_update_ha_state()

    async def media_next_track(self):
        """Send next track command."""
        total = len(self._program_list)
        total = total - 1
        idx = 0
        for item in self._program_list:
            if item[0] == self._program:
                break
            idx = idx + 1
        idx = idx + 1
        if idx > total:
            idx = 0
        self._program = self._program_list[idx][0]
        if len(self._program_list[idx]) > 1:
            self._url = self._program_list[idx][1]
        else:
            self._url = None
        if self._url is None:
            result = await self._try_command(
                "Turning the Gateway next failed.", self._device.send,
                'play_specify_fm', {"id":self._program,"type":0})
        else:
            result = await self._try_command(
                "Turning the Gateway next failed.", self._device.send,
                'play_specify_fm', {"id":self._program,"url":self._url,"type":0})
        if result:
            self.async_schedule_update_ha_state()

    async def media_previous_track(self):
        """Send next track command."""
        total = len(self._program_list)
        total = total - 1
        idx = 0
        for item in self._program_list:
            if item[0] == self._program:
                break
            idx = idx + 1
        idx = idx - 1
        if idx < 0:
            idx = total
        self._program = self._program_list[idx][0]
        if len(self._program_list[idx]) > 1:
            self._url = self._program_list[idx][1]
        else:
            self._url = None
        if self._url is None:
            result = await self._try_command(
                "Turning the Gateway prev failed.", self._device.send,
                'play_specify_fm', {"id":self._program,"type":0})
        else:
            result = await self._try_command(
                "Turning the Gateway prev failed.", self._device.send,
                'play_specify_fm', {"id":self._program,"url":self._url,"type":0})
        if result:
            self.async_schedule_update_ha_state()

    async def set_volume_level(self, volume):
        volset = round(volume * 100)
        result = await self._try_command(
            "Setting the Gateway volume failed.", self._device.send,
            'set_fm_volume', [volset])
        if result:
            self.async_schedule_update_ha_state()

    async def mute_volume(self, mute):
        """Send mute command."""

        if self._muted == False:
            self._volume_back = self._volume
            volume = 0
        else:
            if self._volume_back is not None:
                volume = round(self._volume_back * 100)
            else:
                volume = 10

        result = await self._try_command(
            "Turning the Gateway volume failed.", self._device.send,
            'set_fm_volume', [volume])
        if result:
            if volume == 0:
                self._muted = True
            else:
                self._muted = False
            self.async_schedule_update_ha_state()

    async def async_update(self):
        """Fetch state from Gateway."""
        from miio import DeviceException

        try:
            result = await self.hass.async_add_job(
                self._device.send, 'get_prop_fm', '')
            _LOGGER.debug("Got new state: %s", result)
            program = result.pop('current_program')
            volume = result.pop('current_volume')
            state = result.pop('current_status')
            _LOGGER.debug("Current: program %s volume %s state %s",program,volume,state)

            idx = 0
            for item in self._program_list:
                if item[0] == program:
                    if len(item) > 1:
                        self._url = item[1]
                    else:
                        self._url = None
                    break
                idx = idx + 1
            self._program = program
            if idx >= len(self._source_list):
                self._source = 'Нет в списке'
            else:
                self._source = self._source_list[idx]
            self._volume = float(volume / 100)

            _LOGGER.debug("Got new state: %s", state)

            self._available = True
            if volume == 0:
                self._muted = True
            else:
                self._muted = False

            if state == 'pause':
                self._state = STATE_OFF
            elif state == 'run':
                self._state = STATE_ON
            else:
                _LOGGER.warning(
                    "New state (%s) doesn't match expected values: %s/%s",
                    state, 'pause', 'run')
                self._state = None
            self._state_attrs.update({
                ATTR_STATE_VALUE: state
            })

        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)
