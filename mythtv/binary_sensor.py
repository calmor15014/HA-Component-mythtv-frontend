"""
MythTV Frontend notification service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.mythtv (but not yet)
"""
from homeassistant.components.binary_sensor import BinarySensorEntity

from . import DOMAIN


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MythTV binary sensor platform."""
    sensors = []
    for name in hass.data[DOMAIN].get_tuners():
        sensors.append(MythTVTunerConnectedSensor(name, hass.data[DOMAIN]))
    add_entities(sensors)
    return True


class MythTVTunerConnectedSensor(BinarySensorEntity):
    """Representation of a MythTV Encoder as a binary sensor."""

    def __init__(self, name, backend):
        """Initialize availability sensor."""
        self._state = None
        self._name = name
        self._backend = backend

    @property
    def name(self):
        """Return the name of this binary sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return "connectivity"

    def update(self):
        """Update the state of this sensor (tuner connectivity)."""
        self._state = self._backend.get_tuner_connectivity(self._name)