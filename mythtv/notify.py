"""
MythTV Frontend notification service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.mythfrontend (but not yet)
"""
import asyncio
import logging

from mythtvservicesapi import send as api
import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_TITLE,
    ATTR_TITLE_DEFAULT,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
import homeassistant.helpers.config_validation as cv

# Prerequisite (to be converted to standard PyPI library when available)
# https://github.com/billmeek/MythTVServicesAPI
# TODO: to be changed to new location of API

_LOGGER = logging.getLogger(__name__)

# Set default configuration
DEFAULT_NAME = "MythTV Frontend"
DEFAULT_PORT_FRONTEND = 6547
DEFAULT_ORIGIN = " "
DEFAULT_TIMEOUT = 1.0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT_FRONTEND): cv.port,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(float),
    }
)

ATTR_DISPLAYTIME = "displaytime"

# pylint: disable=unused-argument
@asyncio.coroutine
def async_get_service(hass, config, discovery_info=None):
    """Return the notify service."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    origin = config.get("origin", DEFAULT_ORIGIN)
    timeout = config.get(CONF_TIMEOUT)

    return MythTVFrontendNotificationService(hass, host, port, origin, timeout)


class MythTVFrontendNotificationService(BaseNotificationService):
    """Implement the notification service for MythTV."""

    # pylint: disable=unused-argument
    def __init__(self, hass, host_frontend, port_frontend, origin, timeout):
        """Initialize the MythTV Services API."""

        # Save a reference to the api
        self._api = api
        self._host_frontend = host_frontend
        self._port_frontend = port_frontend
        self._origin = origin
        self._timeout = timeout
        self._fe = api.Send(host=host_frontend, port=port_frontend)

        _LOGGER.debug("Setup MythTV Notifications %s", self._host_frontend)

    @asyncio.coroutine
    def async_send_message(self, message="", **kwargs):
        """Send a message to MythTV frontend."""

        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        endpoint = "Frontend/SendNotification"
        postdata = {
            "Message": title,
            "Description": message,
            "Progress": -1,
            "Origin": self._origin,
        }
        _LOGGER.debug("Trying %s?%s", endpoint, postdata)  # testing
        try:
            result = self._fe.send(
                endpoint=endpoint,
                postdata=postdata,
                opts={"timeout": self._timeout, "debug": True, "wrmi": True},
            )
            _LOGGER.debug(result)  # testing

        except Exception as error:
            _LOGGER.warning("Unable to send MythTV notification: %s", repr(error))
