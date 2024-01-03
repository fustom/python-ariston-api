"""Evo device class for Ariston module."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .const import (
    VelisPlantMode,
    EvoOneDeviceProperties,
    PlantData,
    WaterHeaterMode,
)
from .evo_lydos_device import AristonEvoLydosDevice

_LOGGER = logging.getLogger(__name__)


class AristonEvoOneDevice(AristonEvoLydosDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def plant_data(self) -> PlantData:
        """Final string to get plant data"""
        return PlantData.PD

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return "Dhw"

    @property
    def water_heater_mode(self) -> type[WaterHeaterMode]:
        """Return the water heater mode class"""
        return VelisPlantMode

    @property
    def water_heater_eco_value(self) -> Optional[int]:
        """Get water heater eco value"""
        return self.data.get(EvoOneDeviceProperties.ECO, None)

    @property
    def rm_tm_value(self) -> Optional[str]:
        """Get remaining time value"""
        return self.data.get(EvoOneDeviceProperties.RM_TM, None)

    @property
    def rm_tm_in_minutes(self) -> int:
        """Get remaining time value in minutes"""
        rm_tm = self.rm_tm_value
        if rm_tm is None:
            return -1
        time = datetime.strptime(rm_tm, "%H:%M:%S")
        return time.hour * 60 + time.minute

    def set_eco_mode(self, eco_mode: bool):
        """Set water heater eco_mode"""
        self.api.set_evo_eco_mode(self.gw, eco_mode)
        self.data[EvoOneDeviceProperties.ECO] = eco_mode

    async def async_set_eco_mode(self, eco_mode: bool):
        """Async set water heater eco_mode"""
        await self.api.async_set_evo_eco_mode(self.gw, eco_mode)
        self.data[EvoOneDeviceProperties.ECO] = eco_mode

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_evo_mode(self.gw, VelisPlantMode[operation_mode])
        self.data[EvoOneDeviceProperties.MODE] = VelisPlantMode[operation_mode].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_evo_mode(self.gw, VelisPlantMode[operation_mode])
        self.data[EvoOneDeviceProperties.MODE] = VelisPlantMode[operation_mode].value

    @property
    def is_heating(self) -> Optional[bool]:
        """Get is the water heater heating"""
        return self.data.get(EvoOneDeviceProperties.STATE, None)

    @property
    def max_req_shower(self) -> Optional[str]:
        """Get maximum requestable shower"""
        return self.data.get(EvoOneDeviceProperties.MAX_REQ_SHW, None)

    @property
    def req_shower(self) -> Optional[str]:
        """Get requested shower"""
        return self.data.get(EvoOneDeviceProperties.REQ_SHW, None)

    def set_water_heater_number_of_showers(self, number_of_showers: int):
        """Set water heater number of showers"""
        self.api.set_evo_number_of_showers(self.gw, number_of_showers)
        self.data[EvoOneDeviceProperties.REQ_SHW] = number_of_showers

    async def async_set_water_heater_number_of_showers(self, number_of_showers: int):
        """Async set water heater number of showers"""
        await self.api.async_set_evo_number_of_showers(self.gw, number_of_showers)
        self.data[EvoOneDeviceProperties.REQ_SHW] = number_of_showers

    @property
    def water_heater_maximum_temperature(self) -> Optional[float]:
        """Get water heater maximum temperature"""
        return 0

    @property
    def max_setpoint_temp(self) -> str:
        raise NotImplementedError

    @property
    def anti_legionella_on_off(self) -> str:
        raise NotImplementedError

    @property
    def water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        raise NotImplementedError

    @property
    def water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        raise NotImplementedError

    def set_water_heater_temperature(self, temperature: float) -> None:
        raise NotImplementedError

    async def async_set_water_heater_temperature(self, temperature: float) -> None:
        raise NotImplementedError
