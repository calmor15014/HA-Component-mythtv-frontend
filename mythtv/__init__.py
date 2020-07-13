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

from .const import DOMAIN, MYTHTV_ID

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
        # Myth/GetFrontend has no uuid, so we use "Name" as key
        self._frontends = {}

        self._cancel_discovery = None

        self._host = host
        self._port = port
        self._be = api.Send(host=host, port=port)

    def __call_API(self, endpoint):
        try:
            result = self._be.send(endpoint=endpoint, opts={"timeout": 2})
            return result
        except RuntimeError as error:
            _LOGGER.warning("MythTV Backend API call error - %s", error)
            return None

    def __process_art_response(self, key, response):
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

    def get_video_artwork(self, path):
        filename = path[path.rfind("/") + 1 :]
        _LOGGER.debug("Getting media_image_url for video %s", filename)
        endpoint = f"Video/GetVideoByFileName?FileName={filename}"
        art = self.__call_API(endpoint)
        return self.__process_art_response("Program", art)

    def get_recording_artwork(self, start_time, channel_id):
        _LOGGER.debug("Getting media_image_url for %s on %s", start_time, channel_id)
        endpoint = f"Dvr/GetRecorded?StartTime={start_time}&ChanId={channel_id}"
        art = self.__call_API(endpoint)
        return self.__process_art_response("Program", art)

    def __get_tuners(self):
        result = self.__call_API("Dvr/GetEncoderList")
        if "Encoders" in result["EncoderList"]:
            return result["EncoderList"]["Encoders"]
        else:
            return None

    def get_tuners(self):
        tuners = self.__get_tuners()
        response = []
        if tuners is None:
            return False
        else:
            for t in tuners:
                for input in t["Inputs"]:
                    response.append(input["DisplayName"])
            return response

    def get_tuner_connectivity(self, tuner_name):
        tuners = self.__get_tuners()
        if tuners is None:
            return False
        else:
            for t in tuners:
                connected = t["Connected"] == "true"
                for input in t["Inputs"]:
                    if input["DisplayName"] == tuner_name:
                        return connected
        return False

    def _get_frontends(self):
        """Get frontends with "Name" as key."""
        response = self.__call_API("Myth/GetFrontends?OnLine=1")
        frontend_dict = {}
        for frontend in response["FrontendList"]["Frontends"]:
            frontend_dict[frontend["Name"]] = frontend
        return frontend_dict

    def add_frontend(self, frontend):
        """Add a frontend to dictionary of known frontends."""
        if frontend.unique_id:
            self._frontends.update({frontend.unique_id: frontend})
        else:
            _LOGGER.debug("Could not track frontend %s, no unique_id")

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
                    MYTHTV_ID: val["Name"],
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
