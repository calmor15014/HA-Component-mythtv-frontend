"""
Platform integration for MythTV DVR systems

Sets up API access route (to keep centralized) and common backend for
frontend artwork retrieval.
"""
import logging

# import asyncio #not yet...
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

# Import configuration constants
from homeassistant.const import CONF_PORT, CONF_HOST

# Set the domain name for the integration
DOMAIN = "mythtv"

# Set default platform configuration
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


def setup(hass, config):
    """Set up the MythTV component."""

    host = config[DOMAIN][CONF_HOST]
    port = config[DOMAIN][CONF_PORT]

    try:
        mythtv = MythTV(host, port)
    except:
        _LOGGER.error("Error in setting up MythTV platform")
        return False

    hass.data[DOMAIN] = mythtv

    _LOGGER.debug("Successfully set up MythTV platform")

    return True


class MythTVBackend:
    def __init__(self, host, port):
        # Import MythTV API for communications
        from mythtv_services_api import send as api

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


class MythTV:
    """Set up the functions to access the API"""

    def __init__(self, host, port):
        self._host = host
        self._port = port
        try:
            self._backend = MythTVBackend(host, port)
        except:
            _LOGGER.error("Error adding MythTV backend class")

    def video_artwork(self, pathname):
        return self._process_art_response(
            "VideoMetadataInfo", self._backend.get_video_artwork(pathname)
        )

    def recording_artwork(self, startTime, channelId):
        return self._process_art_response(
            "Program", self._backend.get_recording_artwork(startTime, channelId)
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
