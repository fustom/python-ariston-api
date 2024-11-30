"""Evo device class for Ariston module."""

from __future__ import annotations

import logging

from .const import (
    EvoDeviceProperties,
    LuxPlantMode,
    WaterHeaterMode,
)
from .evo_device import AristonEvoDevice

_LOGGER = logging.getLogger(__name__)


class AristonLydosDevice(AristonEvoDevice):
    """Class representing a physical Lydos Wi-Fi device, it's state and properties."""

    @property
    def water_heater_mode(self) -> type[WaterHeaterMode]:
        """Return the water heater mode class"""
        return LuxPlantMode

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_evo_mode(self.gw, self.water_heater_mode[operation_mode])
        self.data[EvoDeviceProperties.MODE] = self.water_heater_mode[
            operation_mode
        ].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_evo_mode(
            self.gw, self.water_heater_mode[operation_mode]
        )
        self.data[EvoDeviceProperties.MODE] = self.water_heater_mode[
            operation_mode
        ].value
