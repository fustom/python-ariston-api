"""Evo device class for Ariston module."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .const import (
    EvoPlantMode,
    EvoDeviceProperties,
    MedDeviceSettings,
    PlantData,
    WaterHeaterMode,
)
from .evo_lydos_device import AristonEvoLydosDevice

_LOGGER = logging.getLogger(__name__)


class AristonEvoDevice(AristonEvoLydosDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def plant_data(self) -> PlantData:
        """Final string to get plant data"""
        return PlantData.Med

    @property
    def anti_legionella_on_off(self) -> str:
        """Final string to get anti-legionella-on-off"""
        return MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return "Dhw"

    @property
    def water_heater_mode(self) -> type[WaterHeaterMode]:
        """Return the water heater mode class"""
        return EvoPlantMode

    @property
    def max_setpoint_temp(self) -> str:
        return MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE

    @property
    def water_heater_eco_value(self) -> Optional[int]:
        """Get water heater eco value"""
        return self.data.get(EvoDeviceProperties.ECO, None)

    @property
    def rm_tm_value(self) -> Optional[str]:
        """Get remaining time value"""
        return self.data.get(EvoDeviceProperties.RM_TM, None)

    @property
    def rm_tm_in_minutes(self) -> int:
        """Get remaining time value in minutes"""
        rm_tm = self.rm_tm_value
        if rm_tm is None:
            return -1
        time = datetime.strptime(rm_tm, "%H:%M:%S")
        return time.hour * 60 + time.minute

    @property
    def water_heater_power_option_value(self) -> Optional[bool]:
        """Get water heater power option value"""
        return self.data.get(EvoDeviceProperties.PWR_OPT, None)

    @property
    def water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature minimum"""
        return self.plant_settings.get(
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MIN, None
        )

    @property
    def water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater maximum setpoint maximum temperature"""
        return self.plant_settings.get(
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MAX, None
        )

    def set_eco_mode(self, eco_mode: bool):
        """Set water heater eco_mode"""
        self.api.set_evo_eco_mode(self.gw, eco_mode)
        self.data[EvoDeviceProperties.ECO] = eco_mode

    async def async_set_eco_mode(self, eco_mode: bool):
        """Async set water heater eco_mode"""
        await self.api.async_set_evo_eco_mode(self.gw, eco_mode)
        self.data[EvoDeviceProperties.ECO] = eco_mode

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_evo_mode(self.gw, EvoPlantMode[operation_mode])
        self.data[EvoDeviceProperties.MODE] = EvoPlantMode[operation_mode].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_evo_mode(self.gw, EvoPlantMode[operation_mode])
        self.data[EvoDeviceProperties.MODE] = EvoPlantMode[operation_mode].value

    def set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        self.api.set_evo_temperature(self.gw, temperature)
        self.data[EvoDeviceProperties.REQ_TEMP] = temperature

    async def async_set_water_heater_temperature(self, temperature: float):
        """Async set water heater temperature"""
        await self.api.async_set_evo_temperature(self.gw, temperature)
        self.data[EvoDeviceProperties.REQ_TEMP] = temperature
