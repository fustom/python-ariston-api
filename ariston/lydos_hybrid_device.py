"""Lydos hybrid device class for Ariston module."""
from __future__ import annotations

import logging

from .ariston import (
    ConsumptionTimeInterval,
    ConsumptionType,
    LydosPlantMode,
    SeDeviceSettings,
    VelisDeviceProperties,
)
from .velis_device import AristonVelisDevice

_LOGGER = logging.getLogger(__name__)


class AristonLydosHybridDevice(AristonVelisDevice):
    """Class representing a physical device, it's state and properties."""

    async def async_update_state(self) -> None:
        """Update the device states from the cloud"""
        self.data = await self.api.async_get_se_plant_data(self.gw)

    async def async_update_settings(self) -> None:
        """Get device settings wrapper"""
        self.plant_settings = await self.api.async_get_se_plant_settings(self.gw)

    @staticmethod
    def get_water_heater_mode_operation_texts() -> list:
        """Get water heater operation mode texts"""
        return [flag.name for flag in LydosPlantMode]

    @staticmethod
    def get_water_heater_mode_options() -> list:
        """Get water heater operation options"""
        return [flag.value for flag in LydosPlantMode]

    def get_water_anti_leg_value(self) -> bool:
        """Get water heater anti-legionella value"""
        if len(self.plant_settings) == 0:
            _LOGGER.exception("Call async_update_settings() first")
        return self.plant_settings.get(SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF, False)

    def get_water_heater_maximum_setpoint_temperature_minimum(self) -> float:
        """Get water heater maximum setpoint temperature minimum"""
        if len(self.plant_settings) == 0:
            _LOGGER.exception("Call async_update_settings() first")
        return self.plant_settings.get(
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MIN, 0
        )

    def get_water_heater_maximum_setpoint_temperature_maximum(self) -> float:
        """Get water heater maximum setpoint maximum temperature"""
        if len(self.plant_settings) == 0:
            _LOGGER.exception("Call async_update_settings() first")
        return self.plant_settings.get(
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MAX, 0
        )

    def get_water_heater_maximum_setpoint_temperature(self) -> float:
        """Get water heater maximum setpoint temperature value"""
        if len(self.plant_settings) == 0:
            _LOGGER.exception("Call async_update_settings() first")
        return self.plant_settings.get(SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE, 0)

    def get_electric_consumption_for_water_last_two_hours(self) -> int:
        """Get electric consumption for water last value"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    async def _async_get_consumptions_sequences(self) -> None:
        """Get consumption sequence"""
        self.consumptions_sequences = await self.api.async_get_consumptions_sequences(
            self.gw,
            "DhwHeatingPumpElec%2CDhwResistorElec",
        )

    async def async_set_antilegionella(self, anti_leg: bool):
        """Set water heater anti-legionella"""
        await self.api.async_set_lydos_plant_setting(
            self.gw,
            SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF,
            1.0 if anti_leg else 0.0,
            1.0
            if self.plant_settings[SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF]
            else 0.0,
        )
        self.plant_settings[SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF] = anti_leg

    async def async_set_water_heater_operation_mode(self, operation_mode):
        """Set water heater operation mode"""
        await self.api.async_set_lydos_mode(self.gw, LydosPlantMode[operation_mode])
        self.data[VelisDeviceProperties.MODE] = LydosPlantMode[operation_mode].value

    async def async_set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        await self.api.async_set_lydos_temperature(self.gw, temperature)
        self.data[VelisDeviceProperties.REQ_TEMP] = temperature

    async def async_set_power(self, power: bool):
        """Set water heater power"""
        await self.api.async_set_lydos_power(self.gw, power)
        self.data[VelisDeviceProperties.ON] = power

    async def async_set_max_setpoint_temp(self, max_setpoint_temp: float):
        """Set water heater anti-legionella"""
        await self.api.async_set_lydos_plant_setting(
            self.gw,
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE,
            max_setpoint_temp,
            self.plant_settings[SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE],
        )
        self.plant_settings[
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE
        ] = max_setpoint_temp
