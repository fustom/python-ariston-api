"""Velis device class for Ariston module."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from .ariston_api import AristonAPI
from .const import (
    CustomDeviceFeatures,
    DeviceFeatures,
    PlantData,
    VelisBaseDeviceProperties,
    WaterHeaterMode,
)
from .base_device import AristonBaseDevice

_LOGGER = logging.getLogger(__name__)


class AristonVelisBaseDevice(AristonBaseDevice, ABC):
    """Class representing a physical device, it's state and properties."""

    def __init__(
        self,
        api: AristonAPI,
        attributes: dict[str, Any],
    ) -> None:
        super().__init__(api, attributes)
        self.plant_settings: dict[str, Any] = dict()

    @property
    @abstractmethod
    def plant_data(self) -> PlantData:
        """Final string to get plant data"""

    @property
    @abstractmethod
    def water_heater_mode(self) -> type[WaterHeaterMode]:
        """Return the water heater mode class"""

    def update_state(self) -> None:
        """Update the device states from the cloud"""
        self.data = self.api.get_velis_plant_data(self.plant_data, self.gw)

    async def async_update_state(self) -> None:
        """Async update the device states from the cloud"""
        self.data = await self.api.async_get_velis_plant_data(self.plant_data, self.gw)

    def update_settings(self) -> None:
        """Get device settings wrapper"""
        self.plant_settings = self.api.get_velis_plant_settings(
            self.plant_data, self.gw
        )

    async def async_update_settings(self) -> None:
        """Get device settings wrapper"""
        self.plant_settings = await self.api.async_get_velis_plant_settings(
            self.plant_data, self.gw
        )

    def set_power(self, power: bool):
        """Set water heater power"""
        self.api.set_velis_power(self.plant_data, self.gw, power)
        self.data[VelisBaseDeviceProperties.ON] = power

    async def async_set_power(self, power: bool) -> None:
        """Async set water heater power"""
        await self.api.async_set_velis_power(self.plant_data, self.gw, power)
        self.data[VelisBaseDeviceProperties.ON] = power

    @property
    def water_heater_mode_operation_texts(self) -> list[str]:
        """Get water heater operation mode texts"""
        return [flag.name for flag in self.water_heater_mode]

    @property
    def water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return [flag.value for flag in self.water_heater_mode]

    def get_features(self) -> None:
        """Get device features wrapper"""
        super().get_features()
        self.custom_features[CustomDeviceFeatures.HAS_DHW] = True
        self.features[DeviceFeatures.DHW_MODE_CHANGEABLE] = True
        self.update_settings()

    async def async_get_features(self) -> None:
        """Async get device features wrapper"""
        await super().async_get_features()
        self.custom_features[CustomDeviceFeatures.HAS_DHW] = True
        self.features[DeviceFeatures.DHW_MODE_CHANGEABLE] = True
        await self.async_update_settings()

    @property
    def water_heater_mode_value(self) -> Optional[int]:
        """Get water heater mode value"""
        return self.data.get(VelisBaseDeviceProperties.MODE, None)

    @property
    def water_heater_power_value(self) -> Optional[bool]:
        """Get water heater power value"""
        return self.data.get(VelisBaseDeviceProperties.ON, None)
