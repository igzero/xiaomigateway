""" XiaomiGateway init """
import logging
import voluptuous as vol
import asyncio

from datetime import timedelta
from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_TOKEN, EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.util import Throttle
from homeassistant.helpers import discovery
from functools import partial
from homeassistant.components.discovery import (
    CONFIG_SCHEMA, SERVICE_HASSIO
)

REQUIREMENTS = ['python-miio>=0.3.7']

DOMAIN = 'xiaomigateway'

CONF_HOST='host'
CONF_TOKEN='token'
CONF_SID='sid'
CONF_NAME='name'
CONF_SOURCE_LIST = 'source_list'
CONF_PROGRAM_LIST = 'program_list'

LIGHT='light'
SWITCH='switch'
MEDIA_PLAYER='media_player'

ENTITY_CONFIG = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_SID): vol.All(cv.string, vol.Length(min=5, max=21)),
    }
)

MEDIA_CONFIG = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_SOURCE_LIST): [cv.string],
        vol.Optional(CONF_PROGRAM_LIST): [
#            vol.All([cv.positive_int, vol.All(cv.string,default=None),], vol.Length(min=1,max=2)),],
            vol.All([cv.positive_int, vol.All(cv.url,default=None),], vol.Length(min=1,max=2)),],
    }
)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
                vol.Optional(LIGHT, default={}): vol.All(
                    cv.ensure_list,
                    vol.Any(
                        vol.All([ENTITY_CONFIG]),
                    ),
                ),
                vol.Optional(SWITCH, default={}): vol.All(
                    cv.ensure_list,
                    vol.Any(
                        vol.All([ENTITY_CONFIG]),
                    ),
                ),
                vol.Optional(MEDIA_PLAYER, default={}): vol.All(
                    cv.ensure_list,
                    vol.Any(
                        vol.All([MEDIA_CONFIG], vol.Length(max=1)),
                    ),
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

DEFAULT_NAME_RADIO = 'Xiaomi Gateway FM Radio'
DEFAULT_NAME_LIGHT = 'lumi.light.aqcn02'
DEFAULT_NAME_SWITCH = 'lumi.relay.c2acn01'

ATTR_MODEL = 'model'
ATTR_FIRMWARE_VERSION = 'firmware_version'
ATTR_HARDWARE_VERSION = 'hardware_version'

_LOGGER = logging.getLogger(__name__)

ZNLDP12LM = 66
LLRZMK11LM = 54

@asyncio.coroutine
def async_setup(hass, config):
#def setup(hass, config):
    """Set up the Xiaomi Gateway miio platform."""
    from miio import Device, DeviceException

    host = config[DOMAIN].get(CONF_HOST)
    token = config[DOMAIN].get(CONF_TOKEN)

    if host is None or token is None:
        _LOGGER.error("Platform %s not configured",DOMAIN)
        return False

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN]['device'] = None
        hass.data[DOMAIN]['sid'] = []
        hass.data[DOMAIN]['light'] = {"name":[], "sid":[], "device":[]}
        hass.data[DOMAIN]['switch'] = {"name":[], "sid":[], "device":[]}
        hass.data[DOMAIN]['radio'] = {"name":None, "source_list":[], "program_list":[]}
        hass.data[DOMAIN]['power'] = {}
    else:
        hass.data[DOMAIN]['device'] = None
        hass.data[DOMAIN]['sid'].clear()

        hass.data[DOMAIN]['light']["name"].clear()
        hass.data[DOMAIN]['light']["sid"].clear()

        hass.data[DOMAIN]['switch']["name"].clear()
        hass.data[DOMAIN]['switch']["sid"].clear()

        hass.data[DOMAIN]['radio']["name"] = None
        hass.data[DOMAIN]['radio']["source_list"].clear()
        hass.data[DOMAIN]['radio']["program_list"].clear()

        hass.data[DOMAIN]['power'].clear()


    async def xiaomigateway_discovered(service, discovery_info):
        """Perform action when Xiaomi Gateway device(s) has been found."""
        # We don't need to do anything here, the purpose of Home Assistant's
        # discovery service is to just trigger loading of this
        # component, and then its own discovery process kicks in.

    _LOGGER.info("Initializing Xiaomi Gateway with host %s (with token is ...%s)", host, token)

    try:
        miio_device = Device(host, token)
        device_info = miio_device.info()
        if device_info is None:
            _LOGGER.error("Device not ready")
            return False

        sid_list=[]
        sid_list=miio_device.send('get_device_prop',['lumi.0','device_list'])
        cnt=len(sid_list)
        for i in range(cnt):
            if type(sid_list[i]) == str and len(sid_list[i]) > 5:
                if sid_list[i][:5] == 'lumi.':
                    if sid_list[i+1] == LLRZMK11LM or sid_list[i+1] == ZNLDP12LM:
                        hass.data[DOMAIN]['sid'].append(sid_list[i])
        hass.data[DOMAIN]['device'] = miio_device

        _LOGGER.info("SID list %s",hass.data[DOMAIN]['sid'])

# Create list of load components
        components=[]

# List of Light

        i = 0
        if len(config[DOMAIN]['light'][0]) > 0:
            for item in config[DOMAIN]['light']:
                item=config[DOMAIN]['light'][i]
                sid = item['sid']
                _LOGGER.debug("Light SID: %s",sid)
                if sid[:5] != "lumi.":
                    sid = "lumi." + sid
                _LOGGER.debug("Light SID: %s Count: %d",sid,hass.data[DOMAIN]['sid'].count(sid))
                if hass.data[DOMAIN]['sid'].count(sid) == 1:
#                    if sid[:14] != "lumi.158d0003e":
#                        _LOGGER.error("Sid %s is not Aqara LED Bulb")
#                        continue
                    if components.count('light') == 0:
                        _LOGGER.debug("Add Aqara LED Bulb %s",sid)
                        components.append('light')
# Add sid
                    hass.data[DOMAIN]['light']['sid'].append(sid)
                    name = config[DOMAIN]['light'][i].get(CONF_NAME,None)
                    if name is None:
                        name = DEFAULT_NAME_LIGHT + "." + sid
# Add name
                    if hass.data[DOMAIN]['light']['name'].count(name) > 0:
                        name = name + "." + sid
                    hass.data[DOMAIN]['light']['name'].append(name)
# Create socket for each light
                    try:
                        light_device = Device(host, token)
                        light_info = light_device.info()
                        if light_info is None:
# If socket not open, choise first opened socket (miio_device)
                            _LOGGER.error("Device not ready")
                            hass.data[DOMAIN]['light']['device'].append(miio_device)
                        else:
# Else choise opened socket
                            hass.data[DOMAIN]['light']['device'].append(light_device)
                    except DeviceException as light_exc:
                        _LOGGER.error("Error open socket for light:",light_exc)
                i = i + 1

# List of Switch

        i = 0
        if len(config[DOMAIN]['switch'][0]) > 0:
            for item in config[DOMAIN]['switch']:
                item=config[DOMAIN]['switch'][i]
                sid = item['sid']
                if sid[:5] != "lumi.":
                    sid = "lumi." + sid
                _LOGGER.debug("Switch SID: %s Count: %d",sid,hass.data[DOMAIN]['sid'].count(sid))
                if hass.data[DOMAIN]['sid'].count(sid) == 1:
                    _LOGGER.debug("Check Switch")
#                    if sid[:14] != "lumi.158d0003c":
#                        _LOGGER.error("Sid %s is not Aqara Relay")
#                        continue
                    result=miio_device.send('get_device_prop_exp',[[sid,'load_power']])
                    load_power = result[0][0]
                    if load_power < 0.0:
                        continue
                    _LOGGER.debug("Switch GOOD")
                    if components.count('switch') == 0:
                        _LOGGER.debug("Add Aqara Relay %s",sid)
                        components.append('switch')
# Add sid
                    hass.data[DOMAIN]['switch']['sid'].append(sid)
                    name = config[DOMAIN]['switch'][i].get(CONF_NAME,None)
# Add name
                    if name is None:
                        name = DEFAULT_NAME_SWITCH + "." + sid
                    if hass.data[DOMAIN]['switch']['name'].count(name) > 0:
                        name = name + "." + sid
                    hass.data[DOMAIN]['switch']['name'].append(name)
# Create socket for each switch
                    try:
                        switch_device = Device(host, token)
                        switch_info = switch_device.info()
                        if switch_info is None:
# If socket not open, choise first opened socket (miio_device)
                            _LOGGER.error("Device not ready")
                            hass.data[DOMAIN]['switch']['device'].append(miio_device)
                        else:
# Else choise opened socket
                            hass.data[DOMAIN]['switch']['device'].append(switch_device)
                    except DeviceException as switch_exc:
                        _LOGGER.error("Error open socket for switch:",switch_exc)
                i = i + 1

# Radio

        if len(config[DOMAIN]['media_player'][0]) > 0:
            name = None
            name = config[DOMAIN]['media_player'][0].get(CONF_NAME)
            if(name) is None:
                name = DEFAULT_NAME_RADIO
            _LOGGER.debug("MEDIA_PLAYER: %s",config[DOMAIN]['media_player'])
            hass.data[DOMAIN]['radio']['name'] = name
            hass.data[DOMAIN]['radio']['source_list'] = config[DOMAIN]['media_player'][0].get('source_list')
            hass.data[DOMAIN]['radio']['program_list'] = config[DOMAIN]['media_player'][0].get('program_list')

            components.append('media_player')

        _LOGGER.debug("Load Components: %s",components)
        for item in components:
            discovery.load_platform(hass,item,DOMAIN,{},config)

        def stop_xiaomigateway(event):
            """Stop XiaomiGateway Socket."""
            _LOGGER.info("Shutting down XiaomiGateway")
            hass.data[DOMAIN].clear()

    except DeviceException:
        _LOGGER.error("Can't init platform")
        return False
    return True
