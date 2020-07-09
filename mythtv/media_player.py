"""
Support for interface with a MythTV Frontend.

# For more details about this platform, please refer to the documentation at
# https://github.com/calmor15014/HA-Component-mythtv-frontend/
"""
import logging

from mythtvservicesapi import send as api
import voluptuous as vol
import wakeonlan

from . import DOMAIN

# Adding all of the potential options for now, should trim down or implement
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SEEK,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

# Prerequisite (to be converted to standard PyPI library when available)
# https://github.com/billmeek/MythTVServicesAPI

# Set up logging object
_LOGGER = logging.getLogger(__name__)

# set up sysevents for tun_off
CONF_TURN_OFF_SYSEVENT = "turn_off_sysevent"
TURN_OFF_SYSEVENT_OPTIONS = [
    "SYSEVENT01",
    "SYSEVENT02",
    "SYSEVENT03",
    "SYSEVENT04",
    "SYSEVENT05",
    "SYSEVENT06",
    "SYSEVENT07",
    "SYSEVENT08",
    "SYSEVENT09",
    "SYSEVENT10",
    "none",
]

# Set default configuration
DEFAULT_NAME = "MythTV Frontend"
DEFAULT_PORT_FRONTEND = 6547
DEFAULT_ARTWORK_CHOICE = True
DEFAULT_TURN_OFF_SYSEVENT = "none"
DEFAULT_TIMEOUT = 1.0

# Set core supported media_player functions
SUPPORT_MYTHTV_FRONTEND = (
    SUPPORT_PAUSE
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PLAY
    | SUPPORT_STOP
    | SUPPORT_SEEK
    | SUPPORT_TURN_OFF
)

# Set supported media_player functions when volume_control is enabled
SUPPORT_VOLUME_CONTROL = SUPPORT_VOLUME_STEP | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET

# Set up YAML schema
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT_FRONTEND): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MAC): cv.string,
        vol.Optional("show_artwork", default=DEFAULT_ARTWORK_CHOICE): cv.boolean,
        vol.Optional(
            CONF_TURN_OFF_SYSEVENT, default=DEFAULT_TURN_OFF_SYSEVENT
        ): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(float),
    }
)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the MythTV Frontend platform."""
    host_frontend = config.get(CONF_HOST)
    port_frontend = config.get(CONF_PORT)
    mythtv = hass.data[DOMAIN]
    name = config.get(CONF_NAME)
    mac = config.get(CONF_MAC)
    show_artwork = config.get("show_artwork")
    timeout = config.get(CONF_TIMEOUT)
    if config.get(CONF_TURN_OFF_SYSEVENT) in TURN_OFF_SYSEVENT_OPTIONS:
        turn_off = config.get(CONF_TURN_OFF_SYSEVENT)
    else:
        turn_off = "none"

    add_entities(
        [
            MythTVFrontendEntity(
                host_frontend,
                port_frontend,
                mythtv,
                name,
                mac,
                show_artwork,
                turn_off,
                timeout,
            )
        ]
    )
    _LOGGER.info(
        "MythTV Frontend %s:%d added as '%s'", host_frontend, port_frontend, name,
    )


class MythTVFrontendEntity(MediaPlayerEntity):
    """Representation of a MythTV Frontend."""

    def __init__(
        self,
        host_frontend,
        port_frontend,
        mythtv,
        name,
        mac,
        show_artwork,
        turn_off,
        timeout,
    ):
        """Initialize the MythTV API."""

        # Save a reference to the api
        self._host_frontend = host_frontend
        self._port_frontend = port_frontend
        self._name = name
        self._show_artwork = show_artwork
        self._frontend = {}
        self._mac = mac
        self._wol = wakeonlan
        self._volume = {"control": False, "level": 0, "muted": False}
        self._state = STATE_UNKNOWN
        self._last_playing_title = None
        self._media_image_url = None
        self._mythtv = mythtv
        self._fe = api.Send(host=host_frontend, port=port_frontend)
        self._turn_off = turn_off
        self._timeout = timeout
        self._connected = True

    def update(self):
        """Use the API to get the latest status."""
        _LOGGER.debug("MythTVFrontendEntity.api_update()")
        if self._connected:  # only update connected players
            try:
                result = self._fe.send(
                    endpoint="Frontend/GetStatus", opts={"timeout": self._timeout}
                )

                if list(result.keys())[0] in ["Abort", "Warning"]:
                    # If frontend is connected but API fails, MythFrontend state is unknown
                    self.available = False
                    self._state = STATE_UNKNOWN
                    return False

                # Make frontend status values more user-friendly
                self._frontend = result["FrontendStatus"]["State"]

                # Determine state of frontend
                if self._frontend["state"] == "idle":
                    self._state = STATE_IDLE
                elif self._frontend["state"].startswith("Watching"):
                    if self._frontend["playspeed"] == "0":
                        self._state = STATE_PAUSED
                    else:
                        self._state = STATE_PLAYING
                else:
                    self._state = STATE_ON

                # only get artwork from backend if the playing media has changed
                if self._state not in [STATE_PLAYING, STATE_PAUSED]:
                    self._media_image_url = None
                elif self._show_artwork and self._has_playing_media_changed():
                    self._media_image_url = self._get_artwork()

            except RuntimeError as error:
                # It is possible this frontend went offline since the last GetFrontends poll
                self._mythtv._get_frontends()

                # Log error if frontend is not off
                if self._state != STATE_OFF:
                    _LOGGER.warning("Error with '%s' - %s", self._name, error)

                return False

        return True

    def _get_artwork(self):
        # Get artwork from backend using video file or starttime and chanid
        if self._frontend.get("state") == "WatchingVideo":
            return self._mythtv.video_artwork(self._frontend.get("pathname"))
        else:
            start_time = self._frontend.get("starttime").strip("Z")
            channel_id = self._frontend.get("chanid")
            return self._mythtv.recording_artwork(start_time, channel_id)

    def api_send_action(self, action, value=None):
        """Send a command to the Frontend."""
        try:
            result = self._fe.send(
                endpoint="Frontend/SendAction",
                postdata={"Action": action, "Value": value},
                opts={"wrmi": True, "timeout": self._timeout},
            )
            self.update()
        except OSError:
            self._state = STATE_OFF
            return False

        return result

    @property
    def unique_id(self):
        return f"mythtv_{self._name}"

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def connected(self):
        """Return True if entity connected to backend."""
        return self._connected

    @connected.setter
    def connected(self, connected):
        """Set connected attributed and make related changes to entity."""
        self._connected = connected

        if connected:
            # Set volume control flag and level if the volume tag is present
            if "volume" in self._frontend:
                self._volume["control"] = True
                self._volume["level"] = int(self._frontend["volume"])

            # Set mute status if mute tag exists
            if "mute" in self._frontend:
                self._volume["muted"] = self._frontend["mute"] != "0"

            # Update state of newly connected frontend
            self.update()
        else:
            # Remove volume controls while frontend is unavailable
            self._volume["control"] = False

            # Disconnected frontends are 'off'
            self._state = STATE_OFF

    @property
    def volume_level(self):
        """Return volume level from 0 to 1."""
        return self._volume["level"] / 100

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._volume["muted"]

    @property
    def supported_features(self):
        """Get supported features."""
        features = SUPPORT_MYTHTV_FRONTEND
        if self._mac:
            # Add WOL feature
            features |= SUPPORT_TURN_ON
        if self._volume["control"]:
            features |= SUPPORT_VOLUME_CONTROL
        return features

    @property
    def media_title(self):
        """Return the title of current playing media."""
        title = self._frontend.get("title")
        subtitle = self._frontend.get("subtitle", "")
        if subtitle != "":
            title += " - " + subtitle
        try:
            if self._frontend.get("state").startswith("WatchingLiveTV"):
                title += " (Live TV)"
        except AttributeError:
            # ignore error if state is None
            pass
        return title

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        total_seconds = self._frontend.get("totalseconds")
        if total_seconds is not None:
            return int(total_seconds)
        return 0

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        seconds_played = self._frontend.get("secondsplayed")
        if seconds_played is not None:
            return int(seconds_played)
        return 0

    @property
    def media_position_updated_at(self):
        """Last valid time of media position."""
        if self._state == STATE_PLAYING or self._state == STATE_PAUSED:
            return dt_util.utcnow()
        return None

    @property
    def media_image_url(self):
        """Return the media image URL."""
        return self._media_image_url

    def _has_playing_media_changed(self):
        """Determine if media has changed since last update."""
        title = self.media_title
        has_changed = title != self._last_playing_title
        self._last_playing_title = title
        return has_changed

    def volume_up(self):
        """Volume up the media player."""
        self.api_send_action(action="VOLUMEUP")

    def volume_down(self):
        """Volume down media player."""
        self.api_send_action(action="VOLUMEDOWN")

    def set_volume_level(self, volume):
        """Set specific volume level."""
        self.api_send_action(action="SETVOLUME", value=int(volume * 100))

    def mute_volume(self, mute):
        """Send mute command."""
        self.api_send_action(action="MUTE")

    def media_play_pause(self):
        """Simulate play/pause media player."""
        if self._state == STATE_PLAYING:
            self.media_pause()
        elif self._state == STATE_PAUSED:
            self.media_play()

    def media_play(self):
        """Send play command."""
        self.api_send_action(action="PLAY")

    def media_pause(self):
        """Send pause command."""
        self.api_send_action(action="PAUSE")

    def media_next_track(self):
        """Send next track command."""
        self.api_send_action(action="JUMPFFWD")

    def media_previous_track(self):
        """Send previous track command."""
        self.api_send_action(action="JUMPRWND")

    def turn_on(self):
        """Turn the media player on."""
        if self._mac:
            self._wol.send_magic_packet(self._mac)

    def media_seek(self, position):
        """Send seek command."""
        self.api_send_action(action="SEEKABSOLUTE", value=int(position))

    def turn_off(self):
        """Turn the media player off."""
        if self._turn_off != "none":
            # Send the turn-off action
            self.api_send_action(action=self._turn_off)
            # Tell HA the state is unknown to prevent further inputs
            # and errors on unresponsive frontends
            self._state = STATE_UNKNOWN

    def media_stop(self):
        """Stop playback of media"""
        if self._state == STATE_PLAYING or self._state == STATE_PAUSED:
            self.api_send_action(action="ESCAPE")
