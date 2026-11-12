"""Behavioral tests for Galevo property access and controls."""

import asyncio
import unittest
from datetime import date
from unittest.mock import AsyncMock, Mock

from ariston.const import (
    ConsumptionProperties,
    ConsumptionTimeInterval,
    ConsumptionType,
    Currency,
    CustomDeviceFeatures,
    DeviceAttribute,
    DeviceFeatures,
    DeviceProperties,
    GasEnergyUnit,
    GasType,
    MenuItemNames,
    PlantMode,
    PropertyType,
    ThermostatProperties,
    ZoneAttribute,
    ZoneMode,
)
from ariston.galevo_device import AristonGalevoDevice


class AristonGalevoDeviceTests(unittest.TestCase):
    def make_device(self, metric=True):
        api = Mock()
        device = AristonGalevoDevice(
            api,
            {DeviceAttribute.GW: "gw-1", DeviceAttribute.HPMP_SYS: True},
            is_metric=metric,
            language_tag="pt-PT",
        )
        device.features = {
            DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1, ZoneAttribute.NAME: "Living"}]
        }
        device.data = self.make_data()
        device.menu_items = [
            {"id": MenuItemNames.SIGNAL_STRENGTH.value, PropertyType.VALUE: 4, PropertyType.UNIT: "%"},
            {"id": MenuItemNames.CH_RETURN_TEMP.value, PropertyType.VALUE: 38, PropertyType.UNIT: "°C"},
        ]
        return device

    def make_data(self):
        items = []
        for item in DeviceProperties:
            row = {
                "id": item.value,
                PropertyType.ZONE: 0,
                PropertyType.VALUE: 1,
                PropertyType.MIN: 0,
                PropertyType.MAX: 99,
                PropertyType.STEP: 0.5,
                PropertyType.DECIMALS: 1,
                PropertyType.UNIT: "°C",
                PropertyType.OPTIONS: [mode.value for mode in PlantMode],
                PropertyType.OPT_TEXTS: [mode.name for mode in PlantMode],
                PropertyType.EXPIRES_ON: "2026-12-31",
            }
            if item is DeviceProperties.PLANT_MODE:
                row[PropertyType.VALUE] = PlantMode.WINTER.value
            elif item is DeviceProperties.DHW_MODE:
                row[PropertyType.VALUE] = 1
                row[PropertyType.OPTIONS] = [0, 1]
                row[PropertyType.OPT_TEXTS] = ["Off", "On"]
            elif item is DeviceProperties.HYBRID_MODE:
                row[PropertyType.VALUE] = 1
                row[PropertyType.OPTIONS] = [0, 1]
                row[PropertyType.OPT_TEXTS] = ["Eco", "Auto"]
            elif item is DeviceProperties.BUFFER_CONTROL_MODE:
                row[PropertyType.VALUE] = 0
                row[PropertyType.OPTIONS] = [0, 1]
                row[PropertyType.OPT_TEXTS] = ["Disabled", "Enabled"]
            items.append(row)

        for item in ThermostatProperties:
            row = {
                "id": item.value,
                PropertyType.ZONE: 1,
                PropertyType.VALUE: 1,
                PropertyType.MIN: 10,
                PropertyType.MAX: 30,
                PropertyType.STEP: 0.5,
                PropertyType.DECIMALS: 1,
                PropertyType.UNIT: "°C",
                PropertyType.OPTIONS: [mode.value for mode in ZoneMode],
                PropertyType.OPT_TEXTS: [mode.name for mode in ZoneMode],
            }
            if item is ThermostatProperties.ZONE_MODE:
                row[PropertyType.VALUE] = ZoneMode.MANUAL.value
            items.append(row)
        return {"items": items}

    def test_metadata_properties_zone_controls_and_item_lookup_defaults(self):
        device = self.make_device()
        self.assertTrue(device.plant_mode_supported)
        self.assertEqual(device.consumption_type, "Ch%2CCooling")
        self.assertEqual(device.umsys, "si")
        self.assertEqual(device.language_tag, "pt-PT")
        self.assertEqual(device.zones, device.features[DeviceFeatures.ZONES])
        self.assertEqual(device.zone_numbers, [1])
        self.assertEqual(device.water_heater_current_temperature, 1)
        device._set_item_by_id(DeviceProperties.DHW_TEMP, 48)
        device._set_item_by_id(DeviceProperties.DHW_STORAGE_TEMPERATURE, 62)
        self.assertEqual(device.water_heater_current_temperature, 48)
        device.custom_features[DeviceProperties.DHW_STORAGE_TEMPERATURE] = True
        self.assertEqual(device.water_heater_current_temperature, 62)
        device.custom_features[DeviceProperties.DHW_STORAGE_TEMPERATURE] = False
        self.assertEqual(device.water_heater_minimum_temperature, 0)
        self.assertEqual(device.water_heater_maximum_temperature, 99)
        self.assertEqual(device.water_heater_target_temperature, 48)
        self.assertEqual(device.water_heater_temperature_decimals, 1)
        self.assertEqual(device.water_heater_temperature_unit, "°C")
        self.assertEqual(device.water_heater_temperature_step, 0.5)
        self.assertEqual(device.water_heater_mode_operation_texts, ["Off", "On"])
        self.assertEqual(device.water_heater_mode_options, [0, 1])
        self.assertEqual(device.water_heater_mode_value, 1)
        self.assertEqual(device.get_zone_heat_request_value(1), 1)
        self.assertEqual(device.get_zone_economy_temp_value(1), 1)
        self.assertTrue(device.is_plant_in_heat_mode)
        self.assertFalse(device.is_plant_in_cool_mode)
        self.assertTrue(device.is_zone_in_manual_mode(1))
        self.assertFalse(device.is_zone_in_time_program_mode(1))
        self.assertTrue(device.is_zone_mode_options_contains_manual(1))
        self.assertTrue(device.is_zone_mode_options_contains_time_program(1))
        self.assertTrue(device.is_zone_mode_options_contains_off(1))
        self.assertTrue(device.is_plant_mode_options_contains_off)
        self.assertTrue(device.is_plant_mode_options_contains_cooling)
        self.assertEqual(device.holiday_expires_on, "2026-12-31")
        self.assertEqual(device.automatic_thermoregulation, 1)
        self.assertEqual(device.heating_circuit_pressure_value, 1)
        self.assertEqual(device.heating_circuit_pressure_unit, "°C")
        self.assertEqual(device.hybrid_mode, "Auto")
        self.assertEqual(device.hybrid_mode_value, 1)
        self.assertEqual(device.hybrid_mode_options, [0, 1])
        self.assertEqual(device.hybrid_mode_opt_texts, ["Eco", "Auto"])
        self.assertEqual(device.buffer_control_mode, "Disabled")
        self.assertEqual(device.buffer_control_mode_value, 0)
        self.assertEqual(device.buffer_control_mode_options, [0, 1])
        self.assertEqual(device.buffer_control_mode_opt_texts, ["Disabled", "Enabled"])
        self.assertEqual(device.is_quiet_value, 1)
        self.assertEqual(device.ch_flow_setpoint_temp_value, 1)
        self.assertEqual(device.ch_flow_temp_value, 1)
        self.assertEqual(device.outside_temp_value, 1)
        self.assertEqual(device.outside_temp_unit, "°C")
        self.assertEqual(device.ch_flow_setpoint_temp_unit, "°C")
        self.assertEqual(device.ch_flow_temp_unit, "°C")
        self.assertEqual(device.is_flame_on_value, 1)
        self.assertEqual(device.is_heating_pump_on_value, 1)
        self.assertEqual(device.holiday_mode_value, 1)
        self.assertEqual(device.get_zone_mode(1), ZoneMode.MANUAL)
        self.assertEqual(device.get_zone_mode_options(1), [mode.value for mode in ZoneMode])
        self.assertEqual(device.plant_mode, PlantMode.WINTER)
        self.assertEqual(device.plant_mode_options, [mode.value for mode in PlantMode])
        self.assertEqual(device.plant_mode_opt_texts, [mode.name for mode in PlantMode])
        self.assertEqual(device.plant_mode_text, PlantMode.WINTER.name)
        plant_mode_item = next(
            item for item in device.data["items"] if item["id"] == DeviceProperties.PLANT_MODE
        )
        plant_mode_item[PropertyType.VALUE] = PlantMode.UNDEFINED.value
        plant_mode_item[PropertyType.OPTIONS] = [
            mode.value for mode in PlantMode if mode is not PlantMode.UNDEFINED
        ]
        self.assertEqual(device.plant_mode_text, PlantMode.UNDEFINED.name)
        self.assertEqual(device.signal_strength_value, 4)
        self.assertEqual(device.signal_strength_unit, "%")
        self.assertEqual(device.ch_return_temp_value, 38)
        self.assertEqual(device.ch_return_temp_unit, "°C")
        self.assertEqual(device.get_measured_temp_unit(1), "°C")
        self.assertEqual(device.get_measured_temp_decimals(1), 1)
        self.assertEqual(device.get_measured_temp_value(1), 1)
        self.assertEqual(device.get_comfort_temp_min(1), 10)
        self.assertEqual(device.get_comfort_temp_max(1), 30)
        self.assertEqual(device.get_comfort_temp_step(1), 0.5)
        self.assertEqual(device.get_comfort_temp_value(1), 1)
        self.assertEqual(device.get_target_temp_step(1), 0.5)
        self.assertEqual(device.get_target_temp_value(1), 1)

        for property_name in (
            "get_heating_flow_offset_value",
            "get_heating_flow_offset_unit",
            "get_heating_flow_offset_step",
            "get_heating_flow_offset_max",
            "get_heating_flow_offset_min",
            "get_heating_flow_offset_decimals",
            "get_heating_flow_temp_value",
            "get_heating_flow_temp_unit",
            "get_heating_flow_temp_step",
            "get_heating_flow_temp_max",
            "get_heating_flow_temp_min",
            "get_heating_flow_temp_decimals",
        ):
            with self.subTest(property_name=property_name):
                self.assertIsNotNone(getattr(device, property_name)(1))

        self.assertEqual(device._get_item_by_id("missing", PropertyType.VALUE), None)
        self.assertEqual(device._get_item_by_id("missing", PropertyType.VALUE, default=7), 7)
        self.assertIsNone(device._get_menu_item_by_id(-1, PropertyType.VALUE))
        device.data["items"].append({"id": "Other", PropertyType.ZONE: 2, PropertyType.VALUE: 9})
        self.assertIsNone(device._get_item_by_id("Other", PropertyType.VALUE, 1))

        us_device = self.make_device(metric=False)
        self.assertEqual(us_device.umsys, "us")
        us_device.custom_features[CustomDeviceFeatures.HAS_DHW] = False
        self.assertEqual(us_device.consumption_type, "Ch%2CCooling")

    def test_features_state_updates_and_sync_async_control_commands(self):
        device = self.make_device()
        device.features = {DeviceFeatures.HAS_BOILER: True, DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1}]}
        device._get_features()
        self.assertTrue(device.custom_features[CustomDeviceFeatures.HAS_DHW])
        device.api.get_features_for_device.return_value = {DeviceFeatures.DHW_PROG_SUPPORTED: True}
        device.api.get_properties.return_value = self.make_data()
        device.api.get_menu_items.return_value = device.menu_items
        device.get_features()
        self.assertTrue(device.custom_features[CustomDeviceFeatures.HAS_DHW])
        device.update_state()
        self.assertTrue(device.custom_features[CustomDeviceFeatures.HAS_OUTSIDE_TEMP])
        self.assertTrue(device.custom_features[DeviceProperties.DHW_STORAGE_TEMPERATURE])
        self.assertTrue(device.custom_features[DeviceProperties.CH_FLOW_TEMP])
        self.assertTrue(device.custom_features[DeviceProperties.IS_QUIET])

        device.set_water_heater_temperature(54)
        device.set_water_heater_operation_mode("On")
        device.set_automatic_thermoregulation(False)
        device.set_hybrid_mode("Eco")
        device.set_buffer_control_mode("Enabled")
        device.set_is_quiet(False)
        device.set_plant_mode(PlantMode.COOLING)
        device.set_zone_mode(ZoneMode.TIME_PROGRAM, 1)
        device.set_comfort_temp(22, 1)
        device.set_heating_flow_temp(35, 1)
        device.set_heating_flow_offset(2, 1)
        device.set_holiday(date(2026, 12, 25))
        self.assertEqual(device.api.set_property.call_count, 11)
        self.assertTrue(device.data["items"])
        self.assertTrue(device.api.set_holiday.called)
        self.assertTrue(device.holiday_mode_value)
        self.assertEqual(device.holiday_expires_on, "2026-12-25T00:00:00")

        no_features = self.make_device()
        no_features.features = {}
        no_features.api.get_features_for_device.return_value = {
            DeviceFeatures.DHW_MODE_CHANGEABLE: True,
            DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1}],
        }
        no_features.api.get_properties.return_value = self.make_data()
        no_features.api.get_menu_items.return_value = no_features.menu_items
        no_features.update_state()
        no_features.api.get_features_for_device.assert_called_once_with("gw-1")

        device.api.async_get_features_for_device = AsyncMock(return_value={DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1}]})
        device.api.async_get_properties = AsyncMock(return_value=self.make_data())
        device.api.async_get_menu_items = AsyncMock(return_value=device.menu_items)
        device.api.async_set_property = AsyncMock()
        device.api.async_set_holiday = AsyncMock()

        async def async_updates():
            await device.async_get_features()
            await device.async_update_state()
            await device.async_set_water_heater_temperature(53)
            await device.async_set_water_heater_operation_mode("Off")
            await device.async_set_automatic_thermoregulation(True)
            await device.async_set_hybrid_mode("Auto")
            await device.async_set_buffer_control_mode("Disabled")
            await device.async_set_is_quiet(True)
            await device.async_set_plant_mode(PlantMode.WINTER)
            await device.async_set_zone_mode(ZoneMode.MANUAL, 1)
            await device.async_set_comfort_temp(21, 1)
            await device.async_set_heating_flow_temp(36, 1)
            await device.async_set_heating_flow_offset(3, 1)
            await device.async_set_holiday(date(2026, 12, 31))

        asyncio.run(async_updates())
        self.assertEqual(device.api.async_set_property.await_count, 11)
        self.assertEqual(device.holiday_expires_on, "2026-12-31T00:00:00")

        async_no_features = self.make_device()
        async_no_features.features = {}
        async_no_features.api.async_get_features_for_device = AsyncMock(return_value={
            DeviceFeatures.DHW_PROG_SUPPORTED: True,
            DeviceFeatures.ZONES: [{ZoneAttribute.NUM: 1}],
        })
        async_no_features.api.async_get_properties = AsyncMock(return_value=self.make_data())
        async_no_features.api.async_get_menu_items = AsyncMock(return_value=async_no_features.menu_items)

        async def refresh_without_features():
            await async_no_features.async_update_state()

        asyncio.run(refresh_without_features())
        async_no_features.api.async_get_features_for_device.assert_awaited_once_with("gw-1")

    def test_consumption_settings_and_energy_account_paths(self):
        device = self.make_device()
        device.consumptions_settings = {
            ConsumptionProperties.ELEC_COST: 0.25,
            ConsumptionProperties.GAS_COST: 0.1,
            ConsumptionProperties.GAS_TYPE: GasType.NATURAL_GAS.value,
            ConsumptionProperties.CURRENCY: Currency.EUR.value,
            ConsumptionProperties.GAS_ENERGY_UNIT: GasEnergyUnit.KWH.value,
        }
        self.assertEqual(device.elect_cost, 0.25)
        self.assertEqual(device.gas_cost, 0.1)
        self.assertEqual(device.gas_type, GasType.NATURAL_GAS.name)
        self.assertEqual(device.currency, Currency.EUR.name)
        self.assertEqual(device.gas_energy_unit, GasEnergyUnit.KWH.name)
        self.assertEqual(device.get_gas_types(), [item.name for item in GasType])
        self.assertEqual(device.get_currencies(), [item.name for item in Currency])
        self.assertEqual(device.get_gas_energy_units(), [item.name for item in GasEnergyUnit])
        device.consumptions_settings[ConsumptionProperties.GAS_TYPE] = 999
        device.consumptions_settings[ConsumptionProperties.CURRENCY] = 999
        device.consumptions_settings[ConsumptionProperties.GAS_ENERGY_UNIT] = 999
        self.assertIsNone(device.gas_type)
        self.assertIsNone(device.currency)
        self.assertIsNone(device.gas_energy_unit)

        device.set_gas_type("LPG")
        device.set_currency("USD")
        device.set_gas_energy_unit("THERM")
        device.set_elect_cost(0.3)
        device.set_gas_cost(0.2)
        self.assertEqual(device.consumptions_settings[ConsumptionProperties.ELEC_COST], 0.3)
        self.assertEqual(device.api.set_consumptions_settings.call_count, 5)
        device.api.async_set_consumptions_settings = AsyncMock()

        async def update_settings():
            await device.async_set_gas_type("PROPANE")
            await device.async_set_currency("EUR")
            await device.async_set_gas_energy_unit("MEGA_BTU")
            await device.async_set_elect_cost(0.4)
            await device.async_set_gas_cost(0.3)

        asyncio.run(update_settings())
        self.assertEqual(device.api.async_set_consumptions_settings.await_count, 5)
        self.assertEqual(device.consumptions_settings[ConsumptionProperties.GAS_COST], 0.3)

        device.energy_account = {"LastMonth": [{"gas": 3, "elect": 4, "cool": 5}, {"gas": 6, "elect": 7}]}
        self.assertEqual(device.gas_consumption_for_heating_last_month, 3)
        self.assertEqual(device.electricity_consumption_for_heating_last_month, 4)
        self.assertEqual(device.electricity_consumption_for_cooling_last_month, 5)
        self.assertEqual(device.gas_consumption_for_water_last_month, 6)
        self.assertEqual(device.electricity_consumption_for_water_last_month, 7)
        device.energy_account = {"LastMonth": [{"gas": 1, "elect": 2}]}
        self.assertIsNone(device.gas_consumption_for_water_last_month)
        self.assertIsNone(device.electricity_consumption_for_water_last_month)
        device.energy_account = {}
        self.assertIsNone(device.gas_consumption_for_heating_last_month)
        self.assertIsNone(device.electricity_consumption_for_heating_last_month)
        self.assertIsNone(device.electricity_consumption_for_cooling_last_month)

        sequences = [
            {"k": ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY.value, "p": ConsumptionTimeInterval.LAST_MONTH.value, "v": [1, 2]},
            {"k": ConsumptionType.CENTRAL_COOLING_TOTAL_ENERGY.value, "p": ConsumptionTimeInterval.LAST_MONTH.value, "v": [3, 4]},
            {"k": ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY.value, "p": ConsumptionTimeInterval.LAST_DAY.value, "v": [99]},
        ]
        device.consumptions_sequences = sequences
        self.assertEqual(device._calc_energy_account(), {"LastMonth": [{"elect": 3, "cool": 7}]})
        device.api.get_consumptions_sequences.return_value = sequences
        device.api.get_consumptions_settings.return_value = {"saved": True}
        device.api.get_energy_account.return_value = {}
        device.update_energy()
        self.assertEqual(device.energy_account, {"LastMonth": [{"elect": 3, "cool": 7}]})
        self.assertEqual(device.consumptions_settings, {"saved": True})

        device.api.async_get_consumptions_sequences = AsyncMock(return_value=sequences)
        device.api.async_get_consumptions_settings = AsyncMock(return_value={"async": True})
        device.api.async_get_energy_account = AsyncMock(return_value={"LastMonth": [{"gas": 1}]})
        asyncio.run(device.async_update_energy())
        self.assertEqual(device.energy_account, {"LastMonth": [{"gas": 1}]})
        self.assertEqual(device.consumptions_settings, {"async": True})
        device.api.async_get_energy_account.return_value = {"LastMonth": []}
        asyncio.run(device.async_update_energy())
        self.assertEqual(device.energy_account, {"LastMonth": [{"elect": 3, "cool": 7}]})


if __name__ == "__main__":
    unittest.main()
