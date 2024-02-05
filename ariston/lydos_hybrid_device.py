"""Lydos hybrid device class for Ariston module."""
from __future__ import annotations

import logging
from typing import Optional

from .const import (
    ConsumptionTimeInterval,
    ConsumptionType,
    LydosPlantMode,
    PlantData,
    SeDeviceSettings,
    LydosDeviceProperties,
)
from .evo_lydos_device import AristonEvoLydosDevice

_LOGGER = logging.getLogger(__name__)


class AristonLydosHybridDevice(AristonEvoLydosDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def plant_data(self) -> PlantData:
        """Final string to get plant data"""
        return PlantData.Se

    @property
    def anti_legionella_on_off(self) -> str:
        """Final string to get anti-legionella-on-off"""
        return SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return "DhwHeatingPumpElec%2CDhwResistorElec"

    @property
    def water_heater_mode(self) -> type[LydosPlantMode]:
        """Return the water heater mode class"""
        return LydosPlantMode

    @property
    def max_setpoint_temp(self) -> str:
        return SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE

    @property
    def water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature minimum"""
        return self.plant_settings.get(
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MIN, None
        )

    @property
    def water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater maximum setpoint maximum temperature"""
        return self.plant_settings.get(
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MAX, None
        )

    @property
    def electric_consumption_for_water_last_two_hours(self) -> int:
        """Get electric consumption for water last value"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    @property
    def permanent_boost_value(self) -> int:
        """Get permanent boost value"""
        return self.plant_settings.get(SeDeviceSettings.SE_PERMANENT_BOOST_ON_OFF, 0)

    @property
    def anti_cooling_value(self) -> int:
        """Get anti cooling value"""
        return self.plant_settings.get(SeDeviceSettings.SE_ANTI_COOLING_ON_OFF, 0)

    @property
    def anti_cooling_temperature_value(self) -> int:
        """Get anti cooling temperature value"""
        return self.plant_settings.get(SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE, 0)

    @property
    def anti_cooling_temperature_maximum(self) -> int:
        """Get anti cooling temperature maximum"""
        return self.plant_settings.get(SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE_MAX, 0)

    @property
    def anti_cooling_temperature_minimum(self) -> int:
        """Get anti cooling temperature minimum"""
        return self.plant_settings.get(SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE_MIN, 0)

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_lydos_mode(self.gw, LydosPlantMode[operation_mode])
        self.data[LydosDeviceProperties.MODE] = LydosPlantMode[operation_mode].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_lydos_mode(self.gw, LydosPlantMode[operation_mode])
        self.data[LydosDeviceProperties.MODE] = LydosPlantMode[operation_mode].value

    def set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        self.api.set_lydos_temperature(self.gw, temperature)
        self.data[LydosDeviceProperties.REQ_TEMP] = temperature

    async def async_set_water_heater_temperature(self, temperature: float):
        """Async set water heater temperature"""
        await self.api.async_set_lydos_temperature(self.gw, temperature)
        self.data[LydosDeviceProperties.REQ_TEMP] = temperature

    def set_permanent_boost_value(self, boost: float) -> None:
        """Set permanent boost value"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SeDeviceSettings.SE_PERMANENT_BOOST_ON_OFF,
            1.0 if boost else 0.0,
            1.0 if self.permanent_boost_value else 0.0,
        )
        self.plant_settings[SeDeviceSettings.SE_PERMANENT_BOOST_ON_OFF] = boost

    async def async_set_permanent_boost_value(self, boost: float) -> None:
        """Async set permanent boost value"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SeDeviceSettings.SE_PERMANENT_BOOST_ON_OFF,
            1.0 if boost else 0.0,
            1.0 if self.permanent_boost_value else 0.0,
        )
        self.plant_settings[SeDeviceSettings.SE_PERMANENT_BOOST_ON_OFF] = boost

    def set_anti_cooling_value(self, anti_cooling: float) -> None:
        """Set anti cooling value"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SeDeviceSettings.SE_ANTI_COOLING_ON_OFF,
            1.0 if anti_cooling else 0.0,
            1.0 if self.anti_cooling_value else 0.0,
        )
        self.plant_settings[SeDeviceSettings.SE_ANTI_COOLING_ON_OFF] = anti_cooling

    async def async_set_anti_cooling_value(self, anti_cooling: float) -> None:
        """Async set anti cooling value"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SeDeviceSettings.SE_ANTI_COOLING_ON_OFF,
            1.0 if anti_cooling else 0.0,
            1.0 if self.anti_cooling_value else 0.0,
        )
        self.plant_settings[SeDeviceSettings.SE_ANTI_COOLING_ON_OFF] = anti_cooling

    def set_cooling_temperature_value(self, temperature: float) -> None:
        """Set cooling temperature value"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE,
            temperature,
            self.anti_cooling_temperature_value,
        )
        self.plant_settings[SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE] = temperature

    async def async_set_cooling_temperature_value(self, temperature: float) -> None:
        """Async set cooling temperature value"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE,
            temperature,
            self.anti_cooling_temperature_value,
        )
        self.plant_settings[SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE] = temperature
