"""Support for GL-inet routers."""
from __future__ import annotations

from collections import namedtuple
from datetime import timedelta
import logging

import gli_py
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = "192.168.8.1"
DEFAULT_PASSWORD = "goodlife"

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string},
    {vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string}
)


def get_scanner(hass, config):
    """Validate the configuration"""
    scanner = GLinetDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


Device = namedtuple("Device", ["mac", "name", "ip", "last_update"])


class GLinetDeviceScanner(DeviceScanner):
    """This class scans for devices connected to the GLinet."""

    def __init__(self, config):
        """Get host from config."""

        self.host = config[CONF_HOST]
        self.pwd = config[CONF_PASSWORD]

        """Initialize the scanner."""
        self.last_results: list[Device] = []
        self.last_raw_results : list[dict] = [{}]

        self.success_init = self._update_info()
        _LOGGER.info("Scanner initialized")

    def scan_devices(self) -> list[str]:
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return [device.mac for device in self.last_results]

    def get_device_name(self, device: str) -> str | None:
        """Return the name of the given device or None if we don't know."""
        filter_named = [
            result.name for result in self.last_results if result.mac == device
        ]
        if filter_named == "*":
            return None
        if filter_named:
            return filter_named[0]
        return None
    
    def get_extra_attributes(self, device: str) -> dict:
        extra = [result for result in self.last_raw_results if result.mac == device]
        assert(len(extra)==1)
        return extra[0]

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def _update_info(self) -> bool:
        """Check the GLinet for devices.

        Returns boolean if scanning successful.
        """
        _LOGGER.info("Scanning")
        base_url = "http://"+self.host+"/cgi-bin/api/"
        router = gli_py.GLinet(self.pwd, base_url=base_url)
        result = router.connected_clients()

        now = dt_util.now()
        last_results = []
        for device in result:
            last_results.append(
                Device(
                    device["mac"], device["name"], device["ip"], now
                )
            )
        self.last_raw_results = result
        self.last_results = last_results

        _LOGGER.info("Scan successful")
        return True
