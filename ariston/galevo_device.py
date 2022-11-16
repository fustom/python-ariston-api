"""Galevo device class for Ariston module."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from .ariston import (
    AristonAPI,
    ConsumptionProperties,
    Currency,
    CustomDeviceFeatures,
    DeviceFeatures,
    DeviceProperties,
    GasEnergyUnit,
    GasType,
    PlantMode,
    PropertyType,
    ThermostatProperties,
    ZoneMode,
)
from .device import AristonDevice

_LOGGER = logging.getLogger(__name__)


class AristonGalevoDevice(AristonDevice):
    """Class representing a physical device, it's state and properties."""

    def __init__(
        self,
        api: AristonAPI,
        attributes: dict[str, Any],
        is_metric: bool = True,
        language_tag: str = "en-US",
    ) -> None:
        super().__init__(api, attributes)
        self.umsys = "si" if is_metric else "us"
        self.language_tag = language_tag
        self.consumptions_settings: dict[str, Any] = dict()
        self.energy_account: dict[str, Any] = dict()

    async def async_update_state(self) -> None:
        """Update the device states from the cloud"""
        if len(self.features) == 0:
            await self.async_get_features()

        self.data = await self.api.async_get_properties(
            self.gw,
            self.features,
            self.language_tag,
            self.umsys,
        )

        if self.custom_features.get(CustomDeviceFeatures.HAS_OUTSIDE_TEMP) is None:
            temp = self._get_item_by_id(
                DeviceProperties.OUTSIDE_TEMP, PropertyType.VALUE
            )
            max_temp = self._get_item_by_id(
                DeviceProperties.OUTSIDE_TEMP, PropertyType.MAX
            )
            self.custom_features[CustomDeviceFeatures.HAS_OUTSIDE_TEMP] = (
                temp != max_temp
            )

        if self.custom_features.get(DeviceProperties.DHW_STORAGE_TEMPERATURE) is None:
            storage_temp = self._get_item_by_id(
                DeviceProperties.DHW_STORAGE_TEMPERATURE, PropertyType.VALUE
            )
            self.custom_features[DeviceProperties.DHW_STORAGE_TEMPERATURE] = (
                storage_temp is not None
            )

    async def async_get_features(self) -> None:
        """Get device features wrapper"""
        await super().async_get_features()
        self.custom_features[CustomDeviceFeatures.HAS_DHW] = self.features.get(
            DeviceFeatures.HAS_BOILER
        )

    def get_water_heater_current_temperature(self) -> float:
        """Get water heater current temperature"""
        if self.custom_features.get(DeviceProperties.DHW_STORAGE_TEMPERATURE):
            return self._get_item_by_id(
                DeviceProperties.DHW_STORAGE_TEMPERATURE, PropertyType.VALUE
            )
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.VALUE)

    def get_water_heater_minimum_temperature(self) -> float:
        """Get water heater minimum temperature"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.MIN)

    def get_water_heater_maximum_temperature(self) -> float:
        """Get water heater maximum temperature"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.MAX)

    def get_water_heater_target_temperature(self) -> float:
        """Get water heater target temperature"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.VALUE)

    def get_water_heater_temperature_decimals(self) -> int:
        """Get water heater temperature decimals"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.DECIMALS)

    def get_water_heater_temperature_unit(self) -> str:
        """Get water heater temperature unit"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.UNIT)

    def get_water_heater_temperature_step(self) -> str:
        """Get water heater temperature step"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.STEP)

    def get_water_heater_mode_operation_texts(self) -> list[str]:
        """Get water heater operation mode texts"""
        return self._get_item_by_id(DeviceProperties.DHW_MODE, PropertyType.OPT_TEXTS)

    def get_water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return self._get_item_by_id(DeviceProperties.DHW_MODE, PropertyType.OPTIONS)

    def get_water_heater_mode_value(self) -> int:
        """Get water heater mode value"""
        return self._get_item_by_id(DeviceProperties.DHW_MODE, PropertyType.VALUE)

    def get_zone_heat_request_value(self, zone_number: int) -> str:
        """Get zone heat request value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_HEAT_REQUEST, PropertyType.VALUE, zone_number
        )

    def get_zone_economy_temp_value(self, zone_number: int) -> str:
        """Get zone economy temperature value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_ECONOMY_TEMP, PropertyType.VALUE, zone_number
        )

    @staticmethod
    def get_zone_number(zone_number: int) -> str:
        """Get zone number"""
        return f"{zone_number}"

    def get_holiday_expires_on(self) -> str:
        """Get holiday expires on"""
        return self._get_item_by_id(DeviceProperties.HOLIDAY, PropertyType.EXPIRES_ON)

    def get_automatic_thermoregulation(self) -> str:
        """Get automatic thermoregulation"""
        return self._get_item_by_id(
            DeviceProperties.AUTOMATIC_THERMOREGULATION, PropertyType.VALUE
        )

    def get_heating_circuit_pressure_value(self) -> str:
        """Get heating circuit pressure value"""
        return self._get_item_by_id(
            DeviceProperties.HEATING_CIRCUIT_PRESSURE, PropertyType.VALUE
        )

    def get_heating_circuit_pressure_unit(self) -> str:
        """Get heating circuit pressure unit"""
        return self._get_item_by_id(
            DeviceProperties.HEATING_CIRCUIT_PRESSURE, PropertyType.UNIT
        )

    def get_ch_flow_setpoint_temp_value(self) -> str:
        """Get central heating flow setpoint temperature value"""
        return self._get_item_by_id(
            DeviceProperties.CH_FLOW_SETPOINT_TEMP, PropertyType.VALUE
        )

    def get_ch_flow_temp_value(self) -> str:
        """Get central heating flow temperature value"""
        return self._get_item_by_id(DeviceProperties.CH_FLOW_TEMP, PropertyType.VALUE)

    def get_outside_temp_value(self) -> str:
        """Get outside temperature value"""
        return self._get_item_by_id(DeviceProperties.OUTSIDE_TEMP, PropertyType.VALUE)

    def get_outside_temp_unit(self) -> str:
        """Get outside temperature unit"""
        return self._get_item_by_id(DeviceProperties.OUTSIDE_TEMP, PropertyType.UNIT)

    def get_ch_flow_setpoint_temp_unit(self) -> str:
        """Get central heating flow setpoint temperature unit"""
        return self._get_item_by_id(
            DeviceProperties.CH_FLOW_SETPOINT_TEMP, PropertyType.UNIT
        )

    def get_ch_flow_temp_unit(self) -> str:
        """Get central heating flow temperature unit"""
        return self._get_item_by_id(DeviceProperties.CH_FLOW_TEMP, PropertyType.UNIT)

    def get_is_flame_on_value(self) -> bool:
        """Get is flame on value"""
        return self._get_item_by_id(DeviceProperties.IS_FLAME_ON, PropertyType.VALUE)

    def get_holiday_mode_value(self) -> bool:
        """Get holiday mode on value"""
        return self._get_item_by_id(DeviceProperties.HOLIDAY, PropertyType.VALUE)

    def get_zone_mode(self, zone) -> ZoneMode:
        """Get zone mode on value"""
        zone_mode = self._get_item_by_id(
            ThermostatProperties.ZONE_MODE, PropertyType.VALUE, zone
        )

        if zone_mode is None:
            return ZoneMode.UNDEFINED

        return ZoneMode(
            self._get_item_by_id(
                ThermostatProperties.ZONE_MODE, PropertyType.VALUE, zone
            )
        )

    def get_zone_mode_options(self, zone) -> list[int]:
        """Get zone mode on options"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MODE, PropertyType.OPTIONS, zone
        )

    def get_plant_mode(self) -> PlantMode:
        """Get plant mode on value"""
        plant_mode = self._get_item_by_id(
            DeviceProperties.PLANT_MODE, PropertyType.VALUE
        )

        if plant_mode is None:
            return PlantMode.UNDEFINED

        return PlantMode(plant_mode)

    def get_plant_mode_options(self) -> list[int]:
        """Get plant mode on options"""
        return self._get_item_by_id(DeviceProperties.PLANT_MODE, PropertyType.OPTIONS)

    def get_plant_mode_opt_texts(self) -> list[str]:
        """Get plant mode on option texts"""
        return self._get_item_by_id(DeviceProperties.PLANT_MODE, PropertyType.OPT_TEXTS)

    def get_plant_mode_text(self) -> str:
        """Get plant mode on option texts"""
        index = self.get_plant_mode_options().index(self.get_plant_mode())
        return self._get_item_by_id(
            DeviceProperties.PLANT_MODE, PropertyType.OPT_TEXTS
        )[index]

    def get_measured_temp_unit(self, zone) -> str:
        """Get zone measured temp unit"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MEASURED_TEMP, PropertyType.UNIT, zone
        )

    def get_measured_temp_decimals(self, zone) -> int:
        """Get zone measured temp decimals"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MEASURED_TEMP, PropertyType.DECIMALS, zone
        )

    def get_measured_temp_value(self, zone) -> int:
        """Get zone measured temp value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MEASURED_TEMP, PropertyType.VALUE, zone
        )

    def get_comfort_temp_min(self, zone) -> int:
        """Get zone comfort temp min"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.MIN, zone
        )

    def get_comfort_temp_max(self, zone) -> int:
        """Get zone comfort temp max"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.MAX, zone
        )

    def get_comfort_temp_step(self, zone) -> int:
        """Get zone comfort temp step"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.STEP, zone
        )

    def get_comfort_temp_value(self, zone) -> int:
        """Get zone comfort temp value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.VALUE, zone
        )

    def get_heating_flow_offset_value(self, zone) -> int:
        """Get zone heating flow offset value"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.VALUE, zone
        )

    def get_heating_flow_offset_unit(self, zone) -> int:
        """Get zone heating flow offset unit"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.UNIT, zone
        )

    def get_heating_flow_offset_step(self, zone) -> int:
        """Get zone heating flow offset step"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.STEP, zone
        )

    def get_heating_flow_offset_max(self, zone) -> int:
        """Get zone heating flow offset max"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.MAX, zone
        )

    def get_heating_flow_offset_min(self, zone) -> int:
        """Get zone heating flow offset min"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.MIN, zone
        )

    def get_heating_flow_offset_decimals(self, zone) -> int:
        """Get zone heating flow offset decimals"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.DECIMALS, zone
        )

    def get_heating_flow_temp_value(self, zone) -> int:
        """Get zone heating flow temp value"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.VALUE, zone
        )

    def get_heating_flow_temp_unit(self, zone) -> int:
        """Get zone heating flow temp unit"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.UNIT, zone
        )

    def get_heating_flow_temp_step(self, zone) -> int:
        """Get zone heating flow temp step"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.STEP, zone
        )

    def get_heating_flow_temp_max(self, zone) -> int:
        """Get zone heating flow temp max"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.MAX, zone
        )

    def get_heating_flow_temp_min(self, zone) -> int:
        """Get zone heating flow temp min"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.MIN, zone
        )

    def get_heating_flow_temp_decimals(self, zone) -> int:
        """Get zone heating flow temp decimals"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.DECIMALS, zone
        )

    def _get_item_by_id(
        self, item_id: str, item_value: str, zone_number: int = 0
    ) -> Any:
        """Get item attribute from data"""
        if len(self.data) == 0:
            _LOGGER.exception("Call async_update_state() first")
        return next(
            (
                item.get(item_value)
                for item in self.data.get("items", dict())
                if item.get("id") == item_id
                and item.get(PropertyType.ZONE) == zone_number
            ),
            None,
        )

    async def _async_get_consumptions_sequences(self) -> None:
        """Get consumption sequence"""
        self.consumptions_sequences = await self.api.async_get_consumptions_sequences(
            self.gw,
            f"Ch{'%2CDhw' if self.custom_features.get(CustomDeviceFeatures.HAS_DHW) else ''}",
        )

    def get_elect_cost(self) -> float | None:
        """Get electric consumption cost"""
        return self.consumptions_settings.get(ConsumptionProperties.ELEC_COST)

    def get_gas_cost(self) -> float | None:
        """Get gas consumption cost"""
        return self.consumptions_settings.get(ConsumptionProperties.GAS_COST)

    def get_gas_type(self) -> str | None:
        """Get gas type"""
        return GasType(
            self.consumptions_settings.get(ConsumptionProperties.GAS_TYPE)
        ).name

    @staticmethod
    def get_gas_types() -> list[str | None]:
        """Get all gas types"""
        return [c.name for c in GasType]

    async def async_set_gas_type(self, selected: str):
        """Set gas type"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.GAS_TYPE, GasType[selected]
        )

    def get_currency(self) -> str | None:
        """Get gas type"""
        return Currency(
            self.consumptions_settings.get(ConsumptionProperties.CURRENCY)
        ).name

    @staticmethod
    def get_currencies() -> list[str | None]:
        """Get all currency"""
        return [c.name for c in Currency]

    async def async_set_currency(self, selected: str):
        """Set currency"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.CURRENCY, Currency[selected]
        )

    def get_gas_energy_unit(self) -> str | None:
        """Get gas energy unit"""
        return GasEnergyUnit(
            self.consumptions_settings.get(ConsumptionProperties.GAS_ENERGY_UNIT)
        ).name

    @staticmethod
    def get_gas_energy_units() -> list[str | None]:
        """Get all gas energy unit"""
        return [c.name for c in GasEnergyUnit]

    async def async_set_gas_energy_unit(self, selected: str):
        """Set gas energy unit"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.GAS_ENERGY_UNIT, GasEnergyUnit[selected]
        )

    def get_gas_consumption_for_heating_last_month(self) -> int | None:
        """Get gas consumption for heating last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if energy_account_last_month is None:
            return None
        return energy_account_last_month[0]["gas"]

    def get_electricity_consumption_for_heating_last_month(self) -> int | None:
        """Get electricity consumption for heating last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if energy_account_last_month is None:
            return None
        return energy_account_last_month[0]["elect"]

    def get_gas_consumption_for_water_last_month(self) -> int | None:
        """Get gas consumption for water last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if energy_account_last_month is None:
            return None
        return energy_account_last_month[1]["gas"]

    def get_electricity_consumption_for_water_last_month(self) -> int | None:
        """Get electricity consumption for water last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if energy_account_last_month is None:
            return None
        return energy_account_last_month[1]["elect"]

    async def async_set_elect_cost(self, value: float):
        """Set electric cost"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.ELEC_COST, value
        )

    async def async_set_gas_cost(self, value: float):
        """Set gas cost"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.GAS_COST, value
        )

    async def _async_set_consumptions_settings(
        self, consumption_property: str, value: float
    ):
        """Set consumption settings"""
        new_settings = self.consumptions_settings.copy()
        new_settings[consumption_property] = value
        await self.api.async_set_consumptions_settings(self.gw, new_settings)
        self.consumptions_settings[consumption_property] = value

    async def async_set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        await self.async_set_item_by_id(DeviceProperties.DHW_TEMP, temperature)

    async def async_set_water_heater_operation_mode(self, operation_mode):
        """Set water heater operation mode"""
        await self.async_set_item_by_id(
            DeviceProperties.DHW_MODE,
            self._get_item_by_id(
                DeviceProperties.DHW_MODE, PropertyType.OPT_TEXTS
            ).index(operation_mode),
        )

    async def async_set_automatic_thermoregulation(self, auto_thermo: bool):
        """Set automatic thermoregulation"""
        await self.async_set_item_by_id(
            DeviceProperties.AUTOMATIC_THERMOREGULATION, 1.0 if auto_thermo else 0.0
        )

    async def async_set_plant_mode(self, plant_mode: PlantMode):
        """Set plant mode"""
        await self.async_set_item_by_id(DeviceProperties.PLANT_MODE, plant_mode)

    async def async_set_zone_mode(self, zone_mode: ZoneMode, zone):
        """Set zone mode"""
        await self.async_set_item_by_id(ThermostatProperties.ZONE_MODE, zone_mode, zone)

    async def async_set_comfort_temp(self, temp: float, zone):
        """Set comfort temp"""
        await self.async_set_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, temp, zone
        )

    async def async_set_heating_flow_temp(self, temp: float, zone):
        """Set heating flow temp"""
        await self.async_set_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, temp, zone
        )

    async def async_set_heating_flow_offset(self, offset: float, zone):
        """Set heating flow offset"""
        await self.async_set_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, offset, zone
        )

    async def async_set_item_by_id(
        self,
        item_id: str,
        value: float,
        zone_number: int = 0,
    ):
        """Set item attribute on device"""
        current_value = self._get_item_by_id(item_id, PropertyType.VALUE, zone_number)
        await self.api.async_set_property(
            self.gw,
            zone_number,
            self.features,
            item_id,
            value,
            current_value,
            self.umsys,
        )
        for item in self.data.get("items", dict()):
            if item.get("id") == item_id and item.get(PropertyType.ZONE) == zone_number:
                item[PropertyType.VALUE] = value
                break

    async def async_set_holiday(self, holiday_end: date):
        """Set holiday on device"""
        holiday_end_date = (
            None if holiday_end is None else holiday_end.strftime("%Y-%m-%dT00:00:00")
        )

        await self.api.async_set_holiday(self.gw, holiday_end_date)

        for item in self.data.get("items", dict()):
            if item.get("id") == DeviceProperties.HOLIDAY:
                item[PropertyType.VALUE] = False if holiday_end_date is None else True
                item[PropertyType.EXPIRES_ON] = (
                    None if holiday_end_date is None else holiday_end_date
                )
                break

    async def async_update_energy(self) -> None:
        """Update the device energy settings from the cloud"""
        await super().async_update_energy()

        # These settings only for official clients
        self.consumptions_settings = await self.api.async_get_consumptions_settings(
            self.gw
        )
        # Last month consumption in kwh
        self.energy_account = await self.api.async_get_energy_account(self.gw)
