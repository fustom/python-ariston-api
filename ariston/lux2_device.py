"""Lux2 device class for Ariston module."""
from __future__ import annotations

import logging

from .const import EvoDeviceProperties
from .evo_device import AristonEvoDevice

_LOGGER = logging.getLogger(__name__)

class AristonLux2Device(AristonEvoDevice):
    """Class representing a physical device, it's state and properties."""

    def set_water_heater_power_option(self, power_option: bool):
        """Set water heater power option"""
        self.api.set_lux_power_option(self.gw, power_option)
        self.data[EvoDeviceProperties.PWR_OPT] = power_option

    async def async_set_water_heater_power_option(self, power_option: bool):
        """Async set water heater power option"""
        await self.api.async_set_lux_power_option(self.gw, power_option)
        self.data[EvoDeviceProperties.PWR_OPT] = power_option
