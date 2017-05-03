"""
Support for interface with a MythTV Frontend.

#For more details about this platform, please refer to the documentation at
#https://github.com/calmor15014/HA-Component-mythtv-frontend/
"""
import logging

import voluptuous as vol
import MythTVServicesAPI

# Adding all of the potential options for now, should trim down or implement
from homeassistant.components.media_player import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP,
    SUPPORT_PLAY, MediaPlayerDevice, PLATFORM_SCHEMA, SUPPORT_TURN_ON,
    SUPPORT_VOLUME_SET, SUPPORT_SELECT_SOURCE, SUPPORT_STOP)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN, CONF_PORT,
    CONF_MAC, STATE_PLAYING, STATE_IDLE, STATE_PAUSED)
import homeassistant.helpers.config_validation as cv

#To add MythTVServicesAPI if/when added to pip
#WOL requirement for turn-on
REQUIREMENTS = ['wakeonlan==0.2.2']

_LOGGER = logging.getLogger(__name__)

# Implement Volume Control later
#CONF_VOLUME_CONTROL = 'volume_control'

DEFAULT_NAME = 'MythTV Frontend'
DEFAULT_PORT = 6547

SUPPORT_MYTHTV_FRONTEND = SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK | \
    SUPPORT_NEXT_TRACK | SUPPORT_PLAY | \
    SUPPORT_SELECT_SOURCE | SUPPORT_STOP
#   Removed SUPPORT_TURN_OFF since there is no frontend action for that at this moment
#   Perhaps implement that with a system event or something similar?

#Implement Volume Control later    
#SUPPORT_VOLUME_CONTROL = SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_MAC): cv.string,
    #Implement Volume Control later
    #vol.Optional(CONF_VOLUME_CONTROL, default=DEFAULT_VOLUME_CONTROL): cv.bool,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    #"""Setup the MythTV Frontend platform."""

    # Should set up known devices later for discovery option
    #known_devices = hass.data.get(KNOWN_DEVICES_KEY)
    #if known_devices is None:
    #    known_devices = set()
    #    hass.data[KNOWN_DEVICES_KEY] = known_devices

    # Manual configuration
    if config.get(CONF_HOST) is not None:
        host = config.get(CONF_HOST)
        port = config.get(CONF_PORT)
        name = config.get(CONF_NAME)
        mac = config.get(CONF_MAC)
        _LOGGER.info('Trying to start MythTV Frontend')
#       volume_control = config.get(CONF_VOLUME_CONTROL)
    else:
        _LOGGER.warning(
            'Internal error on MythTV Frontend component.')
        return

    # Should set up known devices later for discovery option
    # Only add a device once, so discovered devices do not override manual
    # config.
    #ip_addr = socket.gethostbyname(host)
    #if ip_addr not in known_devices:
    #    known_devices.add(ip_addr)
    add_devices([MythTVFrontendDevice(host, port, name, mac)])
    _LOGGER.info("MythTV Frontend Device %s:%d added as '%s'", host, port, name)
    #else:
    #    _LOGGER.info("Ignoring duplicate Samsung TV %s:%d", host, port)


class MythTVFrontendDevice(MediaPlayerDevice):
    """Representation of a MythTV Frontend."""

    def __init__(self, host, port, name, mac):
        """Initialize the MythTV API."""
        from MythTVServicesAPI import Utilities as api
        from wakeonlan import wol
        # Save a reference to the api
        self._api = api
        self._host = host
        self._port = port
        self._name = name
        self._frontend = {}
        self._mac = mac
        self._wol = wol
#       self._volume_control = volume_control
        self._state = STATE_UNKNOWN

    def update(self):
        # """Retrieve the latest data."""
        return self.api_update()

    def api_update(self):
        # """Use the API to get the latest status."""
        try:
            resultDict = self._api.send(host=self._host, port=self._port, 
                endpoint='Frontend/GetStatus')
            if list(resultDict.keys())[0] in ['Abort', 'Warning']:
                self._state = STATE_OFF
                return False	
            self._frontend = resultDict['FrontendStatus']['State']
            if self._frontend['state'] == 'idle':
                self._state = STATE_IDLE
            elif self._frontend['state'].startswith('Watching'):
                if self._frontend['playspeed'] == '0':
                    self._state = STATE_PAUSED
                else:
                    self._state = STATE_PLAYING
            else:
                self._state = STATE_ON
        except:
            self._state = STATE_OFF
            _LOGGER.warning("Communication error with MythTV Frontend Device '%s' at %s:%d", 
		        self._name, self._host, self._port)
            _LOGGER.warning(self._frontend)
            return False

        return True

    def api_send_action(self, action):
        # """Send a command to the Frontend."""
        try:
            result = self._api.send(host=self._host, port=self._port,
                endpoint='Frontend/SendAction', postdata={'Action': action}, 
                opts={'debug': False, 'wrmi': True})
            self.api_update()
        except (self._exceptions_class.ConnectionClosed, OSError):
            self._state = STATE_OFF
            return False        
        
        return result
        
    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    # @property
    # def volume_level(self):
        # """Return volume level from 0 to 1."""
        # if self._volume_control:
            # #TODO - implement volume control
            # return 0
        # return 0
        
    # @property
    # def is_volume_muted(self):
        # """Boolean if volume is currently muted."""
        # if self.volume_control:
            # return self._muted
        # return False

    @property
    def supported_features(self):
        # Implement volume control later
		if self._mac:
            return SUPPORT_MYTHTV_FRONTEND | SUPPORT_TURN_ON
        else:
            return SUPPORT_MYTHTV_FRONTEND

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return self._frontend.get('title')
    
	# def turn_off(self):
        # """Turn off media player."""
        # if self._config['method'] == 'websocket':
            # self.send_key('KEY_POWER')
        # else:
            # self.send_key('KEY_POWEROFF')
        # # Force closing of remote session to provide instant UI feedback
        # self.get_remote().close()

    # def volume_up(self):
        # """Volume up the media player."""
        # self.send_key('KEY_VOLUP')

    # def volume_down(self):
        # """Volume down media player."""
        # self.send_key('KEY_VOLDOWN')

    # def mute_volume(self, mute):
        # """Send mute command."""
        # self.send_key('KEY_MUTE')

    def media_play_pause(self):
        """Simulate play pause media player."""
        if self._state == STATE_PLAYING:
            self.media_pause()
        elif self._state == STATE_PAUSED:
            self.media_play()

    def media_play(self):
        """Send play command."""
        self._playing = True
        self.api_send_action('PLAYBACK')

    def media_pause(self):
        """Send media pause command to media player."""
        self._playing = False
        self.api_send_action('PAUSE')

    def media_next_track(self):
        """Send next track command."""
        self.api_send_action('NEXT')

    def media_previous_track(self):
        """Send the previous track command."""
        self.api_send_action('PREVIOUS')

    def turn_on(self):
        """Turn the media player on."""
        if self._mac:
            self._wol.send_magic_packet(self._mac)
        #else:
        #    self.send_key('KEY_POWERON')
