"""Velis device class for Ariston module."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from .ariston_api import AristonAPI
from .const import (
    CustomDeviceFeatures,
    DeviceFeatures,
    VelisDeviceAttribute,
    VelisDeviceProperties,
    WheType,
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

    def get_whe_type(self) -> WheType:
        """Get device whe type wrapper"""
        return WheType(
            self.attributes.get(VelisDeviceAttribute.WHE_TYPE, WheType.Unknown)
        )

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

    @abstractmethod
    def update_settings(self) -> None:
        """Get device settings wrapper"""
        raise NotImplementedError

    @abstractmethod
    async def async_update_settings(self) -> None:
        """Get device settings wrapper"""
        raise NotImplementedError

    @abstractmethod
    def get_water_anti_leg_value(self) -> Optional[bool]:
        """Get water heater anti-legionella value"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature minimum"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater maximum setpoint maximum temperature"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_maximum_setpoint_temperature(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature value"""
        raise NotImplementedError

    def get_water_heater_current_temperature(self) -> Optional[float]:
        """Get water heater current temperature"""
        return self.data.get(VelisDeviceProperties.TEMP, None)

    def get_water_heater_minimum_temperature(self) -> float:
        """Get water heater minimum temperature"""
        return 40.0

    def get_water_heater_maximum_temperature(self) -> Optional[float]:
        """Get water heater maximum temperature"""
        return self.get_water_heater_maximum_setpoint_temperature()

    def get_water_heater_target_temperature(self) -> Optional[float]:
        """Get water heater target temperature"""
        return self.data.get(VelisDeviceProperties.REQ_TEMP, None)

    def get_water_heater_temperature_step(self) -> int:
        """Get water heater temperature step"""
        return 1

    def get_water_heater_temperature_decimals(self) -> int:
        """Get water heater temperature decimals"""
        return 0

    def get_water_heater_temperature_unit(self) -> str:
        """Get water heater temperature unit"""
        return "°C"

    def get_water_heater_mode_value(self) -> Optional[int]:
        """Get water heater mode value"""
        return self.data.get(VelisDeviceProperties.MODE, None)

    def get_av_shw_value(self) -> Optional[int]:
        """Get average showers value"""
        return self.data.get(VelisDeviceProperties.AV_SHW, None)

    def get_water_heater_power_value(self) -> Optional[bool]:
        """Get water heater power value"""
        return self.data.get(VelisDeviceProperties.ON, None)

    def get_is_heating(self) -> Optional[bool]:
        """Get is the water heater heating"""
        return self.data.get(VelisDeviceProperties.HEAT_REQ, None)

    @staticmethod
    def get_empty_unit() -> str:
        """Get empty unit"""
        return ""

    @abstractmethod
    def set_antilegionella(self, anti_leg: bool) -> None:
        """Set water heater anti-legionella"""
        raise NotImplementedError

    @abstractmethod
    async def async_set_antilegionella(self, anti_leg: bool) -> None:
        """Async set water heater anti-legionella"""
        raise NotImplementedError

    @abstractmethod
    def set_water_heater_temperature(self, temperature: float) -> None:
        """Set water heater temperature"""
        raise NotImplementedError

    @abstractmethod
    async def async_set_water_heater_temperature(self, temperature: float) -> None:
        """Async set water heater temperature"""
        raise NotImplementedError

    @abstractmethod
    def set_power(self, power: bool) -> None:
        """Set water heater power"""
        raise NotImplementedError

    @abstractmethod
    async def async_set_power(self, power: bool) -> None:
        """Async set water heater power"""
        raise NotImplementedError
