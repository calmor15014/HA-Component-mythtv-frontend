"""
Platform integration for MythTV DVR systems

Sets up API access route (to keep centralized) and common backend for
frontend artwork retrieval.
"""
import logging

from mythtvservicesapi import send as api
# import asyncio #not yet...
import voluptuous as vol

from homeassistant.components.media_player import DOMAIN as MP_DOMAIN
# Import configuration constants
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.event import call_later

from .const import DOMAIN

# Set default port for backend configuration
DEFAULT_PORT = 6544

# Set up config schema
# Not so sure about this part, we aren't creating an entity to borrow from yet
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Set up logging object
_LOGGER = logging.getLogger(__name__)

# How often to poll for connected/disconnected backends
DISCOVERY_INTERVAL = 60


def setup(hass, config):
    """Set up the MythTV component."""

    host = config[DOMAIN][CONF_HOST]
    port = config[DOMAIN][CONF_PORT]

    try:
        mythtv = MythTVBackend(host, port, hass, config)
    except:
        _LOGGER.error("Error in setting up MythTV platform")
        return False

    hass.data[DOMAIN] = mythtv
    if hass.is_running:
        mythtv.start_discovery()
    else:
        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, mythtv.start_discovery())

    _LOGGER.debug("Successfully set up MythTV platform")

    return True


class MythTVBackend:
    """Representation of the MythTV backend."""

    def __init__(self, host, port, hass, config):
        """Initialize a MythTV backend."""
        self._host = host
        self._port = port

        # needed to load discovered frontends
        self.hass = hass
        self.config = config

        # create a dictionary of frontends.
        # Myth/GetFrontend has no uuid, so we use "IP" as key
        self._frontends = {}

        self._cancel_discovery = None

        self._be = api.Send(host=host, port=port)

    def _call_API(self, endpoint):
        result = self._be.send(endpoint=endpoint, opts={"timeout": 2})
        if list(result.keys())[0] in ["Abort", "Warning"]:
            _LOGGER.debug("Backend API call to MythTV backend failed: %s", result)
            return None
        return result

    def get_video_artwork(self, path):
        filename = path[path.rfind("/") + 1 :]
        _LOGGER.debug("Getting media_image_url for video %s", filename)
        endpoint = f"Video/GetVideoByFileName?FileName={filename}"
        return self._call_API(endpoint)

    def get_recording_artwork(self, start_time, channel_id):
        _LOGGER.debug("Getting media_image_url for %s on %s", start_time, channel_id)
        endpoint = f"Dvr/GetRecorded?StartTime={start_time}&ChanId={channel_id}"
        return self._call_API(endpoint)

    def _get_frontends(self):
        """Get frontends with "Name" as key."""
        response = self._call_API("Myth/GetFrontends?OnLine=1")
        frontend_dict = {}
        for frontend in response["FrontendList"]["Frontends"]:
            frontend_dict[frontend["Name"]] = frontend
        return frontend_dict

# pylint: disable=unused-argument
    def _discovery(self, now=None):
        """
        Discover frontends.

        Creates new frontends where needed, otherwise updates their `_connected` attribute.
        """

        frontends = self._get_frontends()
        _LOGGER.debug("Got frontends: %s", frontends)

        for key, val in self._frontends.items():
            if key in frontends:
                val.connected = True
            else:
                val.connected = False

        for key, val in frontends.items():
            if key not in self._frontends:
                # we have discovered a new frontend
                discovery_info = {
                    CONF_HOST: val["IP"],
                    CONF_PORT: val["Port"],
                    CONF_NAME: val["Name"],
                }
                load_platform(self.hass, MP_DOMAIN, DOMAIN, discovery_info, self.config)

        call_later(self.hass, DISCOVERY_INTERVAL, self._discovery)

    def start_discovery(self):
        """Start discovering frontends."""
        self._cancel_discovery = call_later(
            self.hass, DISCOVERY_INTERVAL, self._discovery
        )
        _LOGGER.debug("Started frontend discovery")

    def stop_discovery(self):
        """Stop discovering frontends."""
        self._cancel_discovery()

    def video_artwork(self, pathname):
        return self._process_art_response(
            "VideoMetadataInfo", self.get_video_artwork(pathname)
        )

    def recording_artwork(self, startTime, channelId):
        return self._process_art_response(
            "Program", self.get_recording_artwork(startTime, channelId)
        )

    def _process_art_response(self, key, response):
        try:
            artworks = response.get(key).get("Artwork").get("ArtworkInfos")
            # Handle programs that have no artwork
            if not artworks:
                return None
        except AttributeError:
            return None

        part_url = artworks[0].get("URL")
        _LOGGER.debug("Found artwork: %s", part_url)
        return f"http://{self._host}:{self._port}{part_url}"
