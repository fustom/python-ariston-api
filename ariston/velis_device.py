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
    VelisDeviceProperties,
    WaterHeaterMode,
)
from .device import AristonDevice

_LOGGER = logging.getLogger(__name__)


class AristonVelisDevice(AristonDevice, ABC):
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
    def anti_legionella_on_off(self) -> str:
        """Final string to get anti-legionella-on-off"""

    @property
    @abstractmethod
    def water_heater_mode(self) -> type[WaterHeaterMode]:
        """Return the water heater mode class"""

    @property
    @abstractmethod
    def max_setpoint_temp(self) -> str:
        """Final string to get max setpoint temperature"""

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
        self.data[VelisDeviceProperties.ON] = power

    async def async_set_power(self, power: bool) -> None:
        """Async set water heater power"""
        await self.api.async_set_velis_power(self.plant_data, self.gw, power)
        self.data[VelisDeviceProperties.ON] = power

    @property
    def water_anti_leg_value(self) -> Optional[bool]:
        """Get water heater anti-legionella value"""
        return self.plant_settings.get(self.anti_legionella_on_off, None)

    def set_antilegionella(self, anti_leg: bool):
        """Set water heater anti-legionella"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            self.anti_legionella_on_off,
            1.0 if anti_leg else 0.0,
            1.0 if self.plant_settings[self.anti_legionella_on_off] else 0.0,
        )
        self.plant_settings[self.anti_legionella_on_off] = anti_leg

    async def async_set_antilegionella(self, anti_leg: bool):
        """Async set water heater anti-legionella"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            self.anti_legionella_on_off,
            1.0 if anti_leg else 0.0,
            1.0 if self.plant_settings[self.anti_legionella_on_off] else 0.0,
        )
        self.plant_settings[self.anti_legionella_on_off] = anti_leg

    @property
    def water_heater_mode_operation_texts(self) -> list[str]:
        """Get water heater operation mode texts"""
        return [flag.name for flag in self.water_heater_mode]

    @property
    def water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return [flag.value for flag in self.water_heater_mode]

    def set_max_setpoint_temp(self, max_setpoint_temp: float):
        """Set water heater maximum setpoint temperature"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            self.max_setpoint_temp,
            max_setpoint_temp,
            self.plant_settings[self.max_setpoint_temp],
        )
        self.plant_settings[self.max_setpoint_temp] = max_setpoint_temp

    async def async_set_max_setpoint_temp(self, max_setpoint_temp: float):
        """Async set water heater maximum setpoint temperature"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            self.max_setpoint_temp,
            max_setpoint_temp,
            self.plant_settings[self.max_setpoint_temp],
        )
        self.plant_settings[self.max_setpoint_temp] = max_setpoint_temp

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
    @abstractmethod
    def water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature minimum"""
        raise NotImplementedError

    @property
    @abstractmethod
    def water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater maximum setpoint maximum temperature"""
        raise NotImplementedError

    @property
    def water_heater_maximum_setpoint_temperature(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature value"""
        return self.plant_settings.get(self.max_setpoint_temp, None)

    @property
    def water_heater_minimum_temperature(self) -> float:
        """Get water heater minimum temperature"""
        return 40.0

    @property
    def water_heater_maximum_temperature(self) -> Optional[float]:
        """Get water heater maximum temperature"""
        return self.water_heater_maximum_setpoint_temperature

    @property
    def water_heater_temperature_step(self) -> int:
        """Get water heater temperature step"""
        return 1

    @property
    def water_heater_temperature_decimals(self) -> int:
        """Get water heater temperature decimals"""
        return 0

    @property
    def water_heater_temperature_unit(self) -> str:
        """Get water heater temperature unit"""
        return "°C"

    @property
    def water_heater_mode_value(self) -> Optional[int]:
        """Get water heater mode value"""
        return self.data.get(VelisDeviceProperties.MODE, None)

    @property
    def water_heater_power_value(self) -> Optional[bool]:
        """Get water heater power value"""
        return self.data.get(VelisDeviceProperties.ON, None)
