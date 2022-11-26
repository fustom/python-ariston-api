"""Evo device class for Ariston module."""
from __future__ import annotations

import logging
from typing import Optional

from .const import (
    EvoPlantMode,
    EvoDeviceProperties,
    MedDeviceSettings,
    VelisDeviceProperties,
)
from .velis_device import AristonVelisDevice

_LOGGER = logging.getLogger(__name__)


class AristonEvoDevice(AristonVelisDevice):
    """Class representing a physical device, it's state and properties."""

    def update_state(self) -> None:
        """Update the device states from the cloud"""
        self.data = self.api.get_med_plant_data(self.gw)

    async def async_update_state(self) -> None:
        """Async update the device states from the cloud"""
        self.data = await self.api.async_get_med_plant_data(self.gw)

    def update_settings(self) -> None:
        """Get device settings wrapper"""
        self.plant_settings = self.api.get_med_plant_settings(self.gw)

    async def async_update_settings(self) -> None:
        """Async get device settings wrapper"""
        self.plant_settings = await self.api.async_get_med_plant_settings(self.gw)

    def get_water_heater_mode_operation_texts(self) -> list[str]:
        """Get water heater operation mode texts"""
        return [flag.name for flag in EvoPlantMode]

    def get_water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return [flag.value for flag in EvoPlantMode]

    def get_water_anti_leg_value(self) -> Optional[bool]:
        """Get water heater anti-legionella value"""
        return self.plant_settings.get(
            MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF, None
        )

    def get_water_heater_eco_value(self) -> Optional[int]:
        """Get water heater eco value"""
        return self.data.get(EvoDeviceProperties.ECO, None)

    def get_rm_tm_value(self) -> Optional[str]:
        """Get remaining time value"""
        return self.data.get(EvoDeviceProperties.RM_TM, None)

    def get_water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature minimum"""
        return self.plant_settings.get(
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MIN, None
        )

    def get_water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater maximum setpoint maximum temperature"""
        return self.plant_settings.get(
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MAX, None
        )

    def get_water_heater_maximum_setpoint_temperature(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature value"""
        return self.plant_settings.get(
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE, None
        )

    def _get_consumptions_sequences(self) -> None:
        """Get consumption sequence"""
        self.consumptions_sequences = self.api.get_consumptions_sequences(
            self.gw,
            "Dhw",
        )

    async def _async_get_consumptions_sequences(self) -> None:
        """Async get consumption sequence"""
        self.consumptions_sequences = await self.api.async_get_consumptions_sequences(
            self.gw,
            "Dhw",
        )

    def set_eco_mode(self, eco_mode: bool):
        """Set water heater eco_mode"""
        self.api.set_evo_eco_mode(self.gw, eco_mode)
        self.data[EvoDeviceProperties.ECO] = eco_mode

    async def async_set_eco_mode(self, eco_mode: bool) -> None:
        """Async set water heater eco_mode"""
        await self.api.async_set_evo_eco_mode(self.gw, eco_mode)
        self.data[EvoDeviceProperties.ECO] = eco_mode

    def set_antilegionella(self, anti_leg: bool):
        """Set water heater anti-legionella"""
        self.api.set_evo_plant_setting(
            self.gw,
            MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF,
            1.0 if anti_leg else 0.0,
            1.0
            if self.plant_settings[MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF]
            else 0.0,
        )
        self.plant_settings[MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF] = anti_leg

    async def async_set_antilegionella(self, anti_leg: bool):
        """Async set water heater anti-legionella"""
        await self.api.async_set_evo_plant_setting(
            self.gw,
            MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF,
            1.0 if anti_leg else 0.0,
            1.0
            if self.plant_settings[MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF]
            else 0.0,
        )
        self.plant_settings[MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF] = anti_leg

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_evo_mode(self.gw, EvoPlantMode[operation_mode])
        self.data[VelisDeviceProperties.MODE] = EvoPlantMode[operation_mode].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_evo_mode(self.gw, EvoPlantMode[operation_mode])
        self.data[VelisDeviceProperties.MODE] = EvoPlantMode[operation_mode].value

    def set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        self.api.set_evo_temperature(self.gw, temperature)
        self.data[VelisDeviceProperties.REQ_TEMP] = temperature

    async def async_set_water_heater_temperature(self, temperature: float):
        """Async set water heater temperature"""
        await self.api.async_set_evo_temperature(self.gw, temperature)
        self.data[VelisDeviceProperties.REQ_TEMP] = temperature

    def set_power(self, power: bool):
        """Set water heater power"""
        self.api.set_evo_power(self.gw, power)
        self.data[VelisDeviceProperties.ON] = power

    async def async_set_power(self, power: bool) -> None:
        """Async set water heater power"""
        await self.api.async_set_evo_power(self.gw, power)
        self.data[VelisDeviceProperties.ON] = power

    def set_max_setpoint_temp(self, max_setpoint_temp: float):
        """Set water heater maximum setpoint temperature"""
        self.api.set_evo_plant_setting(
            self.gw,
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE,
            max_setpoint_temp,
            self.plant_settings[MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE],
        )
        self.plant_settings[
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE
        ] = max_setpoint_temp

    async def async_set_max_setpoint_temp(self, max_setpoint_temp: float):
        """Async set water heater maximum setpoint temperature"""
        await self.api.async_set_evo_plant_setting(
            self.gw,
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE,
            max_setpoint_temp,
            self.plant_settings[MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE],
        )
        self.plant_settings[
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE
        ] = max_setpoint_temp
