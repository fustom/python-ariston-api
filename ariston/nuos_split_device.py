"""Nuos split device class for Ariston module."""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from .velis_device import AristonVelisDevice
from .const import (
    NuosSplitOperativeMode,
    NuosSplitProperties,
    PlantData,
    SlpDeviceSettings,
)

_LOGGER = logging.getLogger(__name__)


class AristonNuosSplitDevice(AristonVelisDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def plant_data(self) -> PlantData:
        """Final string to get plant data"""
        return PlantData.Slp

    @property
    def anti_legionella_on_off(self) -> str:
        """Final string to get anti-legionella-on-off"""
        return SlpDeviceSettings.SLP_ANTILEGIONELLA_ON_OFF

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return "DhwHeatingPumpElec%2CDhwResistorElec"

    @property
    def water_heater_mode(self) -> type[NuosSplitOperativeMode]:
        """Return the water heater mode class"""
        return NuosSplitOperativeMode

    @property
    def max_setpoint_temp(self) -> str:
        return SlpDeviceSettings.SLP_MAX_SETPOINT_TEMPERATURE

    @property
    def water_heater_current_temperature(self) -> Optional[float]:
        """Get water heater current temperature"""
        return self.data.get(NuosSplitProperties.WATER_TEMP, None)

    @property
    def water_heater_target_temperature(self) -> Optional[float]:
        """Get water heater target temperature"""
        return self.data.get(NuosSplitProperties.COMFORT_TEMP, None)

    @property
    def water_heater_reduced_temperature(self) -> Optional[float]:
        """Get water heater reduced temperature"""
        return self.data.get(NuosSplitProperties.REDUCED_TEMP, None)

    @property
    def water_heater_maximum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater maximum setpoint temperature minimum"""
        return self.plant_settings.get(
            SlpDeviceSettings.SLP_MAX_SETPOINT_TEMPERATURE_MIN, None
        )

    @property
    def water_heater_maximum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater maximum setpoint maximum temperature"""
        return self.plant_settings.get(
            SlpDeviceSettings.SLP_MAX_SETPOINT_TEMPERATURE_MAX, None
        )

    @property
    def water_heater_minimum_setpoint_temperature(self) -> Optional[float]:
        """Get water heater minimum setpoint temperature value"""
        return self.plant_settings.get(
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE, None
        )

    @property
    def water_heater_minimum_setpoint_temperature_minimum(self) -> Optional[float]:
        """Get water heater minimum setpoint temperature minimum"""
        return self.plant_settings.get(
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE_MIN, None
        )

    @property
    def water_heater_minimum_setpoint_temperature_maximum(self) -> Optional[float]:
        """Get water heater minimum setpoint maximum temperature"""
        return self.plant_settings.get(
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE_MAX, None
        )

    @property
    def water_heater_preheating_on_off(self) -> Optional[bool]:
        """Get water heater preheating on off"""
        return self.plant_settings.get(SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF, None)

    @property
    def water_heater_heating_rate(self) -> Optional[float]:
        """Get water heater heating rate"""
        return self.plant_settings.get(SlpDeviceSettings.SLP_HEATING_RATE, None)

    @property
    def water_heater_boost(self) -> Optional[bool]:
        """Get water heater boost"""
        return self.data.get(NuosSplitProperties.BOOST_ON, None)

    @property
    def water_heater_mode_value(self) -> Optional[int]:
        """Get water heater mode value"""
        return self.data.get(NuosSplitProperties.OP_MODE, None)

    @property
    def holiday_end_date(self) -> Optional[str]:
        """Get the holiday end date.

        Returns the ISO-formatted end date the cloud has on file
        (e.g. ``"2026-08-15T00:00:00"``) when a holiday is scheduled, or
        ``None`` when no holiday is active.
        """
        return self.data.get(NuosSplitProperties.HOLIDAY_UNTIL, None)

    @property
    def holiday_active(self) -> bool:
        """Whether a holiday is currently scheduled.

        The Slp payload does not expose a dedicated boolean: an active
        holiday is signalled by `holidayUntil` being a non-null string,
        and an inactive holiday by `holidayUntil` being ``null``.
        """
        return self.data.get(NuosSplitProperties.HOLIDAY_UNTIL) is not None

    def set_water_heater_boost(self, boost: bool):
        """Set water heater boost"""
        self.api.set_nous_boost(self.gw, boost)
        self.data[NuosSplitProperties.BOOST_ON] = boost

    async def async_set_water_heater_boost(self, boost: bool):
        """Set water heater boost"""
        await self.api.async_set_nous_boost(self.gw, boost)
        self.data[NuosSplitProperties.BOOST_ON] = boost

    def _set_water_heater_temperature(self, temperature: float, reduced: float):
        """Set water heater temperature"""
        self.api.set_nuos_temperature(self.gw, temperature, reduced, self.water_heater_target_temperature, self.water_heater_reduced_temperature)
        # Mirror what the cloud now stores. The /temperatures endpoint sets
        # `comfortTemp` and `reducedTemp`; `procReqTemp` is a separate,
        # device-driven field. Writing to it here did not match what the
        # `water_heater_target_temperature` getter reads back, so the
        # optimistic cache update was invisible until the next refresh.
        self.data[NuosSplitProperties.COMFORT_TEMP] = temperature
        self.data[NuosSplitProperties.REDUCED_TEMP] = reduced

    def set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        if len(self.data) == 0:
            self.update_state()
        reduced = self.water_heater_reduced_temperature
        if reduced is None:
            reduced = 0
        self._set_water_heater_temperature(temperature, reduced)

    async def _async_set_water_heater_temperature(
        self, temperature: float, reduced: float
    ):
        """Async set water heater temperature"""
        await self.api.async_set_nuos_temperature(self.gw, temperature, reduced, self.water_heater_target_temperature, self.water_heater_reduced_temperature)
        # See note in `_set_water_heater_temperature`: the cloud /temperatures
        # endpoint updates `comfortTemp` and `reducedTemp`, so the optimistic
        # cache must mirror those fields, not `procReqTemp`.
        self.data[NuosSplitProperties.COMFORT_TEMP] = temperature
        self.data[NuosSplitProperties.REDUCED_TEMP] = reduced

    async def async_set_water_heater_temperature(self, temperature: float):
        """Async set water heater temperature"""
        if len(self.data) == 0:
            await self.async_update_state()
        reduced = self.water_heater_reduced_temperature
        if reduced is None:
            reduced = 0
        await self._async_set_water_heater_temperature(temperature, reduced)

    def set_water_heater_reduced_temperature(self, temperature: float):
        """Set water heater reduced temperature"""
        if len(self.data) == 0:
            self.update_state()
        current = self.water_heater_current_temperature
        if current is None:
            current = 0
        self._set_water_heater_temperature(current, temperature)

    async def async_set_water_heater_reduced_temperature(self, temperature: float):
        """Set water heater reduced temperature"""
        if len(self.data) == 0:
            await self.async_update_state()
        current = self.water_heater_current_temperature
        if current is None:
            current = self.water_heater_minimum_temperature
        await self._async_set_water_heater_temperature(current, temperature)

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.api.set_nuos_mode(self.gw, NuosSplitOperativeMode[operation_mode])
        # The Nuos cloud payload exposes two distinct fields: `mode` (the
        # plant mode shared with other Velis devices) and `opMode` (the
        # operative mode specific to Nuos: GREEN / COMFORT / FAST / IMEMORY).
        # `set_nuos_mode` posts to `/operativeMode`, so the server updates
        # `opMode`. The `water_heater_mode_value` getter also reads `opMode`,
        # so the optimistic cache update has to mirror that field, not the
        # generic `mode`.
        self.data[NuosSplitProperties.OP_MODE] = NuosSplitOperativeMode[
            operation_mode
        ].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.api.async_set_nuos_mode(
            self.gw, NuosSplitOperativeMode[operation_mode]
        )
        # See note in `set_water_heater_operation_mode`: the cloud
        # /operativeMode endpoint updates `opMode`, which is also what the
        # `water_heater_mode_value` getter reads.
        self.data[NuosSplitProperties.OP_MODE] = NuosSplitOperativeMode[
            operation_mode
        ].value

    def set_min_setpoint_temp(self, min_setpoint_temp: float):
        """Set water heater minimum setpoint temperature"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE,
            min_setpoint_temp,
            self.plant_settings[SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE],
        )
        self.plant_settings[
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE
        ] = min_setpoint_temp

    async def async_set_min_setpoint_temp(self, min_setpoint_temp: float):
        """Async set water heater minimum setpoint temperature"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE,
            min_setpoint_temp,
            self.plant_settings[SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE],
        )
        self.plant_settings[
            SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE
        ] = min_setpoint_temp

    def set_preheating(self, preheating: bool):
        """Set water heater preheating"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF,
            preheating,
            self.plant_settings[SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF],
        )
        self.plant_settings[SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF] = preheating

    async def async_set_preheating(self, preheating: bool):
        """Async set water heater preheating"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF,
            preheating,
            self.plant_settings[SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF],
        )
        self.plant_settings[SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF] = preheating

    def set_heating_rate(self, heating_rate: float):
        """Set water heater heating rate"""
        self.api.set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SlpDeviceSettings.SLP_HEATING_RATE,
            heating_rate,
            self.plant_settings[SlpDeviceSettings.SLP_HEATING_RATE],
        )
        self.plant_settings[SlpDeviceSettings.SLP_HEATING_RATE] = heating_rate

    async def async_set_heating_rate(self, heating_rate: float):
        """Async set water heater heating rate"""
        await self.api.async_set_velis_plant_setting(
            self.plant_data,
            self.gw,
            SlpDeviceSettings.SLP_HEATING_RATE,
            heating_rate,
            self.plant_settings[SlpDeviceSettings.SLP_HEATING_RATE],
        )
        self.plant_settings[SlpDeviceSettings.SLP_HEATING_RATE] = heating_rate

    @staticmethod
    def _create_holiday_end_date(holiday_end: Optional[date]) -> Optional[str]:
        """Format a holiday end date for the cloud payload.

        Returns ``None`` when ``holiday_end`` is ``None``, which the cloud
        interprets as "clear the holiday".
        """
        return (
            None
            if holiday_end is None
            else holiday_end.strftime("%Y-%m-%dT00:00:00")
        )

    def set_holiday(self, holiday_end: Optional[date]) -> None:
        """Set or clear the holiday on this Nuos device.

        Pass a ``datetime.date`` to schedule the holiday end, or ``None`` to
        clear an active holiday.
        """
        holiday_end_date = self._create_holiday_end_date(holiday_end)
        self.api.set_velis_slp_holiday(self.gw, holiday_end_date)
        self.data[NuosSplitProperties.HOLIDAY_UNTIL] = holiday_end_date

    async def async_set_holiday(self, holiday_end: Optional[date]) -> None:
        """Async set or clear the holiday on this Nuos device.

        Pass a ``datetime.date`` to schedule the holiday end, or ``None`` to
        clear an active holiday.
        """
        holiday_end_date = self._create_holiday_end_date(holiday_end)
        await self.api.async_set_velis_slp_holiday(self.gw, holiday_end_date)
        self.data[NuosSplitProperties.HOLIDAY_UNTIL] = holiday_end_date
