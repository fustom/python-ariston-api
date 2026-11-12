"""Behavioral tests for BSB plant and zone controls."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from ariston.bsb_device import AristonBsbDevice
from ariston.const import (
    BsbDeviceProperties,
    BsbOperativeMode,
    BsbZoneMode,
    BsbZoneProperties,
    DeviceAttribute,
    PropertyType,
)


class AristonBsbDeviceTests(unittest.TestCase):
    def make_data(self):
        return {
            BsbDeviceProperties.DHW_COMF_TEMP: {
                PropertyType.MIN: 40,
                PropertyType.MAX: 65,
                PropertyType.STEP: 1,
                PropertyType.VALUE: 55,
            },
            BsbDeviceProperties.DHW_REDU_TEMP: {
                PropertyType.MIN: 30,
                PropertyType.MAX: 50,
                PropertyType.STEP: 0.5,
                PropertyType.VALUE: 40,
            },
            BsbDeviceProperties.DHW_MODE: {PropertyType.VALUE: BsbOperativeMode.ON.value},
            BsbDeviceProperties.DHW_TEMP: 48,
            BsbDeviceProperties.FLAME: True,
            BsbDeviceProperties.OUT_TEMP: 12.5,
            BsbDeviceProperties.ZONES: {
                "1": {
                    BsbZoneProperties.MODE: {
                        PropertyType.VALUE: BsbZoneMode.MANUAL.value,
                        PropertyType.ALLOWED_OPTIONS: [
                            BsbZoneMode.OFF.value,
                            BsbZoneMode.TIME_PROGRAM.value,
                            BsbZoneMode.MANUAL.value,
                        ],
                    },
                    BsbZoneProperties.CH_COMF_TEMP: {
                        PropertyType.MIN: 15,
                        PropertyType.MAX: 24,
                        PropertyType.STEP: 0.5,
                        PropertyType.VALUE: 21,
                    },
                    BsbZoneProperties.CH_RED_TEMP: {
                        PropertyType.MIN: 10,
                        PropertyType.MAX: 18,
                        PropertyType.STEP: 0.5,
                        PropertyType.VALUE: 17,
                    },
                    BsbZoneProperties.COOLING_ON: False,
                    BsbZoneProperties.ROOM_TEMP: 20.5,
                }
            },
        }

    def make_device(self, data=None):
        api = Mock()
        device = AristonBsbDevice(api, {DeviceAttribute.GW: "gw-1"})
        device.data = data if data is not None else self.make_data()
        return device

    def test_properties_modes_and_zone_temperature_metadata(self):
        device = self.make_device()
        self.assertEqual(device.consumption_type, "Ch%2CDhw")
        self.assertFalse(device.plant_mode_supported)
        self.assertEqual(device.zone_numbers, [1])
        self.assertEqual(device.get_zone(1), device.zones["1"])
        self.assertEqual(device.get_zone(2), {})
        self.assertEqual(device.get_zone_ch_comf_temp(1)[PropertyType.VALUE], 21)
        self.assertEqual(device.get_zone_ch_red_temp(1)[PropertyType.VALUE], 17)
        self.assertEqual(device.get_zone_mode(1), BsbZoneMode.MANUAL)
        self.assertEqual(device.get_zone_mode(2), BsbZoneMode.UNDEFINED)
        self.assertEqual(device.get_zone_mode_options(1), [0, 1, 3])
        self.assertTrue(device.is_zone_in_manual_mode(1))
        self.assertFalse(device.is_zone_in_time_program_mode(1))
        self.assertTrue(device.is_zone_mode_options_contains_manual(1))
        self.assertTrue(device.is_zone_mode_options_contains_time_program(1))
        self.assertTrue(device.is_zone_mode_options_contains_off(1))
        self.assertTrue(device.is_plant_in_heat_mode)
        self.assertFalse(device.is_plant_in_cool_mode)
        self.assertTrue(device.is_flame_on_value)
        self.assertEqual(device.water_heater_current_temperature, 48)
        self.assertEqual(device.water_heater_minimum_temperature, 40)
        self.assertEqual(device.water_heater_reduced_minimum_temperature, 30)
        self.assertEqual(device.water_heater_target_temperature, 55)
        self.assertEqual(device.water_heater_reduced_temperature, 40)
        self.assertEqual(device.water_heater_maximum_temperature, 65)
        self.assertEqual(device.water_heater_reduced_maximum_temperature, 50)
        self.assertEqual(device.water_heater_temperature_step, 1)
        self.assertEqual(device.water_heater_reduced_temperature_step, 0.5)
        self.assertEqual(device.water_heater_temperature_decimals, 1)
        self.assertEqual(device.water_heater_temperature_unit, "°C")
        self.assertEqual(device.water_heater_mode_operation_texts, [mode.name for mode in BsbOperativeMode])
        self.assertEqual(device.water_heater_mode_options, [mode.value for mode in BsbOperativeMode])
        self.assertEqual(device.water_heater_mode_value, BsbOperativeMode.ON.value)
        self.assertEqual(device.get_comfort_temp_min(1), 15)
        self.assertEqual(device.get_comfort_temp_max(1), 24)
        self.assertEqual(device.get_target_temp_step(1), 0.5)
        self.assertEqual(device.get_comfort_temp_step(1), 0.5)
        self.assertEqual(device.get_target_temp_value(1), 21)
        self.assertEqual(device.get_comfort_temp_value(1), 21)
        self.assertEqual(device.get_reduced_temp_min(1), 10)
        self.assertEqual(device.get_reduced_temp_max(1), 18)
        self.assertEqual(device.get_reduced_temp_step(1), 0.5)
        self.assertEqual(device.get_reduced_temp_value(1), 17)
        self.assertEqual(device.get_measured_temp_value(1), 20.5)
        self.assertEqual(device.get_measured_temp_decimals(1), 1)
        self.assertEqual(device.get_measured_temp_unit(1), "°C")
        self.assertEqual(device.outside_temp_value, 12.5)
        self.assertEqual(device.outside_temp_unit, "°C")

        device.data[BsbDeviceProperties.ZONES]["1"][BsbZoneProperties.MODE][PropertyType.VALUE] = BsbZoneMode.TIME_PROGRAM.value
        self.assertTrue(device.is_zone_in_time_program_mode(1))
        device.data[BsbDeviceProperties.ZONES]["1"][BsbZoneProperties.COOLING_ON] = True
        self.assertTrue(device.is_plant_in_cool_mode)
        self.assertFalse(device.is_plant_in_heat_mode)

    def test_sync_and_async_state_feature_and_control_updates(self):
        device = self.make_device({})
        expected_data = self.make_data()
        device.api.get_bsb_plant_data.return_value = expected_data
        device.api.get_features_for_device.return_value = {"hasMetering": True}
        device.update_state()
        device.get_features()
        self.assertEqual(device.data, expected_data)
        self.assertTrue(device.features["hasMetering"])
        self.assertTrue(device.custom_features["hasDhw"])
        self.assertTrue(device.custom_features["hasOutsideTemp"])

        device.set_water_heater_temperature(56)
        device.set_water_heater_reduced_temperature(41)
        device.set_water_heater_operation_mode("OFF")
        device.set_zone_mode(BsbZoneMode.MANUAL_NIGHT, 1)
        device.set_comfort_temp(22, 1)
        device.set_reduced_temp(16, 1)
        self.assertEqual(device.data[BsbDeviceProperties.DHW_COMF_TEMP][PropertyType.VALUE], 48)
        self.assertEqual(device.data[BsbDeviceProperties.DHW_REDU_TEMP][PropertyType.VALUE], 41)
        self.assertEqual(device.data[BsbDeviceProperties.DHW_MODE][PropertyType.VALUE], BsbOperativeMode.OFF.value)
        self.assertEqual(device.get_zone_mode(1), BsbZoneMode.MANUAL_NIGHT)
        self.assertEqual(device.get_comfort_temp_value(1), 22)
        self.assertEqual(device.get_reduced_temp_value(1), 16)
        device.api.set_bsb_temperature.assert_called()
        device.api.set_bsb_mode.assert_called_once_with("gw-1", BsbOperativeMode.OFF)
        device.api.set_bsb_zone_mode.assert_called_once()
        self.assertEqual(device.api.set_bsb_zone_temperature.call_count, 2)

        device.api.async_get_bsb_plant_data = AsyncMock(return_value=self.make_data())
        device.api.async_get_features_for_device = AsyncMock(return_value={"async": True})
        device.api.async_set_bsb_temperature = AsyncMock()
        device.api.async_set_bsb_mode = AsyncMock()
        device.api.async_set_bsb_zone_mode = AsyncMock()
        device.api.async_set_bsb_zone_temperature = AsyncMock()

        async def async_updates():
            await device.async_update_state()
            await device.async_get_features()
            await device.async_set_water_heater_temperature(57)
            await device.async_set_water_heater_reduced_temperature(42)
            await device.async_set_water_heater_operation_mode("ON")
            await device.async_set_zone_mode(BsbZoneMode.OFF, 1)
            await device.async_set_comfort_temp(23, 1)
            await device.async_set_reduced_temp(15, 1)

        asyncio.run(async_updates())
        self.assertEqual(device.features, {"async": True})
        self.assertEqual(device.data[BsbDeviceProperties.DHW_COMF_TEMP][PropertyType.VALUE], 48)
        self.assertEqual(device.data[BsbDeviceProperties.DHW_REDU_TEMP][PropertyType.VALUE], 42)
        self.assertEqual(device.data[BsbDeviceProperties.DHW_MODE][PropertyType.VALUE], BsbOperativeMode.ON.value)
        self.assertEqual(device.get_zone_mode(1), BsbZoneMode.OFF)
        device.api.async_set_bsb_temperature.assert_awaited()
        device.api.async_set_bsb_zone_temperature.assert_awaited()

    def test_zone_metadata_defaults_and_empty_state_setter_fallbacks(self):
        device = self.make_device({})
        self.assertEqual(device.zones, {})
        self.assertEqual(device.zone_numbers, [])
        self.assertEqual(device.get_zone_ch_comf_temp(8), {})
        self.assertEqual(device.get_zone_ch_red_temp(8), {})
        self.assertEqual(device.get_comfort_temp_min(8), 15)
        self.assertEqual(device.get_comfort_temp_max(8), 24)
        self.assertEqual(device.get_comfort_temp_step(8), 0.5)
        self.assertEqual(device.get_comfort_temp_value(8), 0)
        self.assertEqual(device.get_reduced_temp_min(8), 10)
        self.assertEqual(device.get_reduced_temp_max(8), 18)
        self.assertEqual(device.get_reduced_temp_step(8), 0.5)
        self.assertEqual(device.get_reduced_temp_value(8), 0)
        self.assertEqual(device.get_measured_temp_value(8), 0)
        self.assertFalse(device.is_flame_on_value)
        self.assertEqual(device.water_heater_current_temperature, None)
        self.assertEqual(device.outside_temp_value, 0)

        device.api.get_bsb_plant_data.return_value = self.make_data()
        device.set_comfort_temp(20, 1)
        self.assertEqual(device.data[BsbDeviceProperties.ZONES]["1"][BsbZoneProperties.CH_COMF_TEMP][PropertyType.VALUE], 20)

        async_device = self.make_device({})
        async_device.api.async_get_bsb_plant_data = AsyncMock(return_value=self.make_data())
        async_device.api.async_set_bsb_zone_temperature = AsyncMock()

        async def update_before_setting():
            await async_device.async_set_reduced_temp(14, 1)

        asyncio.run(update_before_setting())
        async_device.api.async_get_bsb_plant_data.assert_awaited_once_with("gw-1")
        self.assertEqual(
            async_device.data[BsbDeviceProperties.ZONES]["1"][BsbZoneProperties.CH_RED_TEMP][PropertyType.VALUE],
            14,
        )

    def test_dhw_and_zone_setters_load_empty_state_and_apply_zero_fallbacks(self):
        sparse_data = self.make_data()
        sparse_data.pop(BsbDeviceProperties.DHW_TEMP)
        sparse_data[BsbDeviceProperties.DHW_REDU_TEMP].pop(PropertyType.VALUE)

        sync_temperature = self.make_device({})
        sync_temperature.api.get_bsb_plant_data.return_value = sparse_data
        sync_temperature.set_water_heater_temperature(53)
        self.assertEqual(
            sync_temperature.api.set_bsb_temperature.call_args.args[1:3],
            (53, 0),
        )

        sync_reduced = self.make_device({})
        sync_reduced.api.get_bsb_plant_data.return_value = self.make_data()
        sync_reduced.data = {}
        sync_reduced.api.get_bsb_plant_data.return_value.pop(BsbDeviceProperties.DHW_TEMP)
        sync_reduced.set_water_heater_reduced_temperature(39)
        self.assertEqual(
            sync_reduced.api.set_bsb_temperature.call_args.args[1:3],
            (0, 39),
        )

        sync_zone_reduced = self.make_device({})
        sync_zone_reduced.api.get_bsb_plant_data.return_value = self.make_data()
        sync_zone_reduced.set_reduced_temp(13, 1)
        self.assertEqual(
            sync_zone_reduced.api.set_bsb_zone_temperature.call_args.args[2:4],
            (21, 13),
        )

        async_temperature = self.make_device({})
        async_sparse_data = self.make_data()
        async_sparse_data.pop(BsbDeviceProperties.DHW_TEMP)
        async_sparse_data[BsbDeviceProperties.DHW_REDU_TEMP].pop(PropertyType.VALUE)
        async_temperature.api.async_get_bsb_plant_data = AsyncMock(return_value=async_sparse_data)
        async_temperature.api.async_set_bsb_temperature = AsyncMock()
        async_reduced = self.make_device({})
        async_reduced_data = self.make_data()
        async_reduced_data.pop(BsbDeviceProperties.DHW_TEMP)
        async_reduced.api.async_get_bsb_plant_data = AsyncMock(return_value=async_reduced_data)
        async_reduced.api.async_set_bsb_temperature = AsyncMock()
        async_zone_comfort = self.make_device({})
        async_zone_comfort.api.async_get_bsb_plant_data = AsyncMock(return_value=self.make_data())
        async_zone_comfort.api.async_set_bsb_zone_temperature = AsyncMock()

        async def set_after_load():
            await async_temperature.async_set_water_heater_temperature(52)
            await async_reduced.async_set_water_heater_reduced_temperature(38)
            await async_zone_comfort.async_set_comfort_temp(22, 1)

        asyncio.run(set_after_load())
        async_temperature.api.async_set_bsb_temperature.assert_awaited_once()
        self.assertEqual(
            async_temperature.api.async_set_bsb_temperature.await_args.args[1:3],
            (52, 0),
        )
        self.assertEqual(
            async_reduced.api.async_set_bsb_temperature.await_args.args[1:3],
            (0, 38),
        )
        async_zone_comfort.api.async_get_bsb_plant_data.assert_awaited_once_with("gw-1")
        async_zone_comfort.api.async_set_bsb_zone_temperature.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
