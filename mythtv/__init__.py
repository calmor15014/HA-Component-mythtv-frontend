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

    def get_frontends(self):
        result = self.__call_API("Myth/GetFrontends")
        if "Frontends" in result["FrontendList"]:
            return result["FrontendList"]["Frontends"]
        else:
            return None

    def get_tuners(self):
        result = self.__call_API("Dvr/GetEncoderList")
        if "Encoders" in result["EncoderList"]:
            return result["EncoderList"]["Encoders"]
        else:
            return None

class MythTV:
    """Set up the functions to access the API"""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        try:
            self.backend = MythTVBackend(host, port)
        except:
            _LOGGER.error("Error adding MythTV backend class")

    def get_online_status(self, frontend):
        frontends = self.backend.get_frontends()
        if frontends is None:
            return False
        else:
            for fe in frontends:
                if frontend == fe["Name"] or frontend == fe["IP"]:
                    return fe["OnLine"] == "1"
            return False
        
    def get_tuners(self):
        tuners = self.backend.get_tuners()
        response = []
        if tuners is None:
            return False
        else:
            for t in tuners:
                for input in t["Inputs"]:
                    response.append(input["DisplayName"])
            return response

    def get_tuner_connectivity(self, tuner_name):
        tuners = self.backend.get_tuners()
        if tuners is None:
            return False
        else:
            for t in tuners:
                connected = t["Connected"] == "true"
                for input in t["Inputs"]:
                    if input["DisplayName"] == tuner_name:
                        return connected
        return False