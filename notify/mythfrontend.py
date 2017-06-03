"""
MythTV Frontend notification service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.mythfrontend/ (not yet)
"""
import asyncio
import logging

import aiohttp
import voluptuous as vol

from homeassistant.const import (
    ATTR_ICON, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD,
    CONF_PROXY_SSL)
from homeassistant.components.notify import (
    ATTR_TITLE, ATTR_TITLE_DEFAULT, ATTR_DATA, PLATFORM_SCHEMA,
    BaseNotificationService)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

# Prerequisite (to be converted to standard PyPI library when available)
# https://github.com/billmeek/MythTVServicesAPI

_LOGGER = logging.getLogger(__name__)

# Set default configuration
DEFAULT_NAME = 'MythTV Frontend'
DEFAULT_PORT_FRONTEND = 6547
DEFAULT_ORIGIN = '.'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT_FRONTEND): cv.port,
})

ATTR_DISPLAYTIME = 'displaytime'


@asyncio.coroutine
def async_get_service(hass, config, discovery_info=None):
    """Return the notify service."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    origin = config.get('origin', DEFAULT_ORIGIN)

    return MythTVFrontendNotificationService(hass, host, port, origin)


class MythTVFrontendNotificationService(BaseNotificationService):
    """Implement the notification service for MythTV."""

    # pylint: disable=unused-argument
    def __init__(self, hass, host, port, origin):
        """Initialize the service.
        """
        from mythtv_services_api import send as api
        # Save a reference to the api
        self._api = api
        self._host = host
        self._port = port
        self._origin = origin

        _LOGGER.debug("Setup MythTV Notifications %s", self._host)

    @asyncio.coroutine
    def async_send_message(self, message="", **kwargs):
        """Send a message to MythTV."""

        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        endpoint = 'Frontend/SendNotification'
        postdata = {'Message': title, 'Description': message, 'Progress': -1,
                    'Origin': self._origin}
        _LOGGER.debug("Trying %s?%s", endpoint, postdata)  # testing
        try:
            result = self._api.send(host=self._host,
                                    port=self._port,
                                    endpoint=endpoint,
                                    postdata=postdata,
                                    opts={'timeout': 1, 'debug': True,
                                          'wrmi': True})
            _LOGGER.debug(result)  # testing

        except Exception as error:
            _LOGGER.warning("Unable to send MythTV notification: %s", error)
