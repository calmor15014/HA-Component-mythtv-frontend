"""
Support for interface with a MythTV Frontend.

#For more details about this platform, please refer to the documentation at
#https://github.com/calmor15014/HA-Component-mythtv-frontend/
"""
import logging
import subprocess
import sys

import voluptuous as vol

# Adding all of the potential options for now, should trim down or implement
from homeassistant.components.media_player import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP,
    SUPPORT_PLAY, MediaPlayerDevice, PLATFORM_SCHEMA, SUPPORT_TURN_ON,
    SUPPORT_VOLUME_SET, SUPPORT_STOP)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN, CONF_PORT,
    CONF_MAC, STATE_PLAYING, STATE_IDLE, STATE_PAUSED)
import homeassistant.helpers.config_validation as cv

# Prerequisite (to be converted to standard PyPI library when available)
# https://github.com/billmeek/MythTVServicesAPI

# WOL requirement for turn_on
REQUIREMENTS = ['wakeonlan==0.2.2']

_LOGGER = logging.getLogger(__name__)

# Implement Volume Control later
# CONF_VOLUME_CONTROL = 'volume_control'

DEFAULT_NAME = 'MythTV Frontend'
DEFAULT_PORT = 6547

SUPPORT_MYTHTV_FRONTEND = SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK | \
                          SUPPORT_NEXT_TRACK | SUPPORT_PLAY | \
                          SUPPORT_STOP
#   Removed SUPPORT_TURN_OFF since there is no frontend action for that
#   Perhaps implement that with a system event or something similar?

# TODO: Implement Volume Control later
# SUPPORT_VOLUME_CONTROL = SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_MAC): cv.string,
    # Implement Volume Control later
    # vol.Optional(CONF_VOLUME_CONTROL, default=DEFAULT_VOLUME_CONTROL): cv.bool,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the MythTV Frontend platform."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    name = config.get(CONF_NAME)
    mac = config.get(CONF_MAC)
    _LOGGER.info('Connecting to MythTV Frontend')
    # volume_control = config.get(CONF_VOLUME_CONTROL)

    add_devices([MythTVFrontendDevice(host, port, name, mac)])
    _LOGGER.info("MythTV Frontend device %s:%d added as '%s'", host, port,
                 name)


class MythTVFrontendDevice(MediaPlayerDevice):
    """Representation of a MythTV Frontend."""

    def __init__(self, host, port, name, mac):
        """Initialize the MythTV API."""
        from mythtv_services_api import send as api
        from wakeonlan import wol
        # Save a reference to the api
        self._api = api
        self._host = host
        self._port = port
        self._name = name
        self._frontend = {}
        self._mac = mac
        self._wol = wol
        # self._volume_control = volume_control
        self._state = STATE_UNKNOWN
        self._playing = False

    def update(self):
        """Retrieve the latest data."""
        return self.api_update()

    def api_update(self):
        """Use the API to get the latest status."""
        try:
            result = self._api.send(host=self._host, port=self._port,
                                    endpoint='Frontend/GetStatus')
            # _LOGGER.debug(result)  # testing
            if list(result.keys())[0] in ['Abort', 'Warning']:
                # If ping succeeds but API fails, MythFrontend state is unknown
                if self._ping_host():
                    self._state = STATE_UNKNOWN
                # If ping fails also, MythFrontend device is off/unreachable
                else:
                    self._state = STATE_OFF
                return False
            self._frontend = result['FrontendStatus']['State']
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
            _LOGGER.warning(
                "Communication error with MythTV Frontend Device '%s' at %s:%d",
                self._name, self._host, self._port)
            _LOGGER.warning(self._frontend)
            return False

        return True

    # Reference: device_tracker/ping.py
    def _ping_host(self):
        """Ping the host to see if API status has some errors."""
        if sys.platform == "win32":
            ping_cmd = ['ping', '-n 1', '-w 1000', self._host]
        else:
            ping_cmd = ['ping', '-nq', '-c1', '-W1', self._host]
        pinger = subprocess.Popen(ping_cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
        try:
            pinger.communicate()
            return pinger.returncode == 0
        except subprocess.CalledProcessError:
            _LOGGER.warning("Mythfrontned ping error for '%s' at '%s'",
                            self._name, self._host)
            return False

    def api_send_action(self, action):
        """Send a command to the Frontend."""
        try:
            result = self._api.send(host=self._host, port=self._port,
                                    endpoint='Frontend/SendAction',
                                    postdata={'Action': action},
                                    opts={'debug': False, 'wrmi': True})
            # _LOGGER.debug(result)  # testing
            self.api_update()
        except OSError:
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
        """Get supported features."""
        # Implement volume control later
        if self._mac:
            return SUPPORT_MYTHTV_FRONTEND | SUPPORT_TURN_ON
        else:
            return SUPPORT_MYTHTV_FRONTEND

    @property
    def media_title(self):
        """Return the title of current playing media."""
        title = self._frontend.get('title')
        try:
            if self._frontend.get('state').startswith('WatchingLiveTV'):
                title += " (Live TV)"
        except AttributeError:
            # ignore error if state is None
            pass
        return title

    # @property
    # def media_image_url(self):
    #     """Return the media image URL."""
    #     return self._frontend.get()

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
        """Simulate play/pause media player."""
        # _LOGGER.debug("_state is %s" % self._state)
        if self._state == STATE_PLAYING:
            self.media_pause()
        elif self._state == STATE_PAUSED:
            self.media_play()

    def media_play(self):
        """Send play command."""
        self._playing = True
        self.api_send_action('PLAY')

    def media_pause(self):
        """Send pause command."""
        self._playing = False
        self.api_send_action('PAUSE')

    def media_next_track(self):
        """Send next track command."""
        self.api_send_action('NEXT')

    def media_previous_track(self):
        """Send previous track command."""
        self.api_send_action('PREVIOUS')

    def turn_on(self):
        """Turn the media player on."""
        if self._mac:
            self._wol.send_magic_packet(self._mac)
