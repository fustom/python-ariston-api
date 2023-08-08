"""Lux device class for Ariston module."""
from __future__ import annotations

import logging
from typing import Optional

from .const import (
    LuxPlantMode,
    EvoDeviceProperties,
    EvoLydosDeviceProperties,
    WaterHeaterMode
)
from .evo_device import AristonEvoDevice

_LOGGER = logging.getLogger(__name__)


class AristonLuxDevice(AristonEvoDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def water_heater_mode(self) -> type[WaterHeaterMode]:
        """Return the water heater mode class"""
        return LuxPlantMode

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_evo_mode(self.gw, LuxPlantMode[operation_mode])
        self.data[EvoDeviceProperties.MODE] = LuxPlantMode[operation_mode].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_evo_mode(self.gw, LuxPlantMode[operation_mode])
        self.data[EvoDeviceProperties.MODE] = LuxPlantMode[operation_mode].value

    @property
    def water_heater_target_temperature(self) -> Optional[float]:
        """Get water heater target temperature"""
        if self.data.get(EvoDeviceProperties.MODE) == LuxPlantMode.BOOST:
            return self.water_heater_maximum_setpoint_temperature_maximum
        else:
            return self.data.get(EvoLydosDeviceProperties.REQ_TEMP, None)
