"""Behavioral tests for the water-heater device models."""

import asyncio
import unittest
from datetime import date
from unittest.mock import AsyncMock, Mock, call

from ariston.const import (
    ConsumptionTimeInterval,
    ConsumptionType,
    DeviceAttribute,
    EvoDeviceProperties,
    EvoLydosDeviceProperties,
    EvoOneDeviceProperties,
    EvoPlantMode,
    LuxPlantMode,
    LydosDeviceProperties,
    LydosPlantMode,
    MedDeviceSettings,
    NuosSplitOperativeMode,
    NuosSplitProperties,
    SeDeviceSettings,
    SlpDeviceSettings,
    VelisBaseDeviceProperties,
    VelisDeviceProperties,
    VelisPlantMode,
)
from ariston.evo_device import AristonEvoDevice
from ariston.evo_one_device import AristonEvoOneDevice
from ariston.lux2_device import AristonLux2Device
from ariston.lux_device import AristonLuxDevice
from ariston.lydos_device import AristonLydosDevice
from ariston.lydos_hybrid_device import AristonLydosHybridDevice
from ariston.nuos_split_device import AristonNuosSplitDevice
from ariston.velis_device import AristonVelisDevice


class AristonDeviceModelTests(unittest.TestCase):
    def make_device(self, device_type, data=None):
        api = Mock()
        device = device_type(api, {DeviceAttribute.GW: "gw-1"})
        device.data = data or {}
        return device

    def test_evo_and_evo_lydos_properties_and_setters(self):
        device = self.make_device(
            AristonEvoDevice,
            {
                EvoDeviceProperties.ECO: True,
                EvoDeviceProperties.RM_TM: "01:35:00",
                EvoDeviceProperties.PWR_OPT: False,
                EvoDeviceProperties.MODE: EvoPlantMode.PROGRAM.value,
                EvoDeviceProperties.REQ_TEMP: 54,
                EvoLydosDeviceProperties.TEMP: 47,
                EvoLydosDeviceProperties.AV_SHW: 2,
                EvoLydosDeviceProperties.HEAT_REQ: True,
                EvoLydosDeviceProperties.ANTI_LEG: False,
            },
        )
        device.plant_settings = {
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MIN: 40,
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MAX: 80,
        }

        self.assertEqual(device.water_heater_eco_value, True)
        self.assertEqual(device.rm_tm_value, "01:35:00")
        self.assertEqual(device.rm_tm_in_minutes, 95)
        self.assertFalse(device.water_heater_power_option_value)
        self.assertEqual(device.water_heater_current_temperature, 47)
        self.assertEqual(device.water_heater_target_temperature, 54)
        self.assertEqual(device.av_shw_value, 2)
        self.assertTrue(device.is_heating)
        self.assertFalse(device.is_antileg)
        self.assertEqual(device.water_heater_maximum_setpoint_temperature_minimum, 40)
        self.assertEqual(device.water_heater_maximum_setpoint_temperature_maximum, 80)
        self.assertEqual(device.water_heater_mode, EvoPlantMode)
        self.assertEqual(device.consumption_type, "Dhw")
        device.data.pop(EvoDeviceProperties.RM_TM)
        self.assertEqual(device.rm_tm_in_minutes, -1)

        device.set_eco_mode(False)
        device.set_water_heater_operation_mode("MANUAL")
        device.set_water_heater_temperature(50)
        self.assertEqual(device.data[EvoDeviceProperties.ECO], False)
        self.assertEqual(device.data[EvoDeviceProperties.MODE], EvoPlantMode.MANUAL.value)
        self.assertEqual(device.data[EvoDeviceProperties.REQ_TEMP], 50)
        device.api.set_evo_eco_mode.assert_called_once_with("gw-1", False)
        device.api.set_evo_mode.assert_called_once_with("gw-1", EvoPlantMode.MANUAL)
        device.api.set_evo_temperature.assert_called_once_with("gw-1", 50)

        device.api.async_set_evo_eco_mode = AsyncMock()
        device.api.async_set_evo_mode = AsyncMock()
        device.api.async_set_evo_temperature = AsyncMock()

        async def set_values():
            await device.async_set_eco_mode(True)
            await device.async_set_water_heater_operation_mode("PROGRAM")
            await device.async_set_water_heater_temperature(58)

        asyncio.run(set_values())
        self.assertTrue(device.data[EvoDeviceProperties.ECO])
        self.assertEqual(device.data[EvoDeviceProperties.MODE], EvoPlantMode.PROGRAM.value)
        self.assertEqual(device.data[EvoDeviceProperties.REQ_TEMP], 58)
        device.api.async_set_evo_eco_mode.assert_awaited_once_with("gw-1", True)
        device.api.async_set_evo_mode.assert_awaited_once_with("gw-1", EvoPlantMode.PROGRAM)
        device.api.async_set_evo_temperature.assert_awaited_once_with("gw-1", 58)

    def test_evo_one_properties_and_sync_async_commands(self):
        device = self.make_device(
            AristonEvoOneDevice,
            {
                EvoOneDeviceProperties.TEMP: 46,
                EvoOneDeviceProperties.AV_SHW: 3,
                EvoOneDeviceProperties.ECO: 1,
                EvoOneDeviceProperties.RM_TM: "00:45:00",
                EvoOneDeviceProperties.STATE: True,
                EvoOneDeviceProperties.MAX_REQ_SHW: "3",
                EvoOneDeviceProperties.REQ_SHW: "2",
                VelisBaseDeviceProperties.MODE: VelisPlantMode.NIGHT.value,
                VelisBaseDeviceProperties.ON: True,
            },
        )

        self.assertEqual(device.water_heater_current_temperature, 46)
        self.assertEqual(device.consumption_type, "Dhw")
        self.assertEqual(device.av_shw_value, 3)
        self.assertEqual(device.water_heater_eco_value, 1)
        self.assertEqual(device.rm_tm_in_minutes, 45)
        device.data.pop(EvoOneDeviceProperties.RM_TM)
        self.assertEqual(device.rm_tm_in_minutes, -1)
        self.assertTrue(device.is_heating)
        self.assertEqual(device.max_req_shower, "3")
        self.assertEqual(device.req_shower, "2")
        self.assertEqual(device.water_heater_mode_value, VelisPlantMode.NIGHT.value)
        self.assertTrue(device.water_heater_power_value)
        self.assertEqual(device.water_heater_mode_options, [mode.value for mode in VelisPlantMode])

        device.set_eco_mode(False)
        device.set_water_heater_operation_mode("MANUAL")
        device.set_water_heater_number_of_showers(1)
        self.assertFalse(device.data[EvoOneDeviceProperties.ECO])
        self.assertEqual(device.data[VelisBaseDeviceProperties.MODE], VelisPlantMode.MANUAL.value)
        self.assertEqual(device.data[EvoOneDeviceProperties.REQ_SHW], 1)
        device.api.set_evo_number_of_showers.assert_called_once_with("gw-1", 1)

        device.api.async_set_evo_eco_mode = AsyncMock()
        device.api.async_set_evo_mode = AsyncMock()
        device.api.async_set_evo_number_of_showers = AsyncMock()

        async def set_values():
            await device.async_set_eco_mode(True)
            await device.async_set_water_heater_operation_mode("NIGHT")
            await device.async_set_water_heater_number_of_showers(2)

        asyncio.run(set_values())
        self.assertTrue(device.data[EvoOneDeviceProperties.ECO])
        self.assertEqual(device.data[VelisBaseDeviceProperties.MODE], VelisPlantMode.NIGHT.value)
        self.assertEqual(device.data[EvoOneDeviceProperties.REQ_SHW], 2)
        device.api.async_set_evo_number_of_showers.assert_awaited_once_with("gw-1", 2)

    def test_velis_update_settings_power_and_antilegionella(self):
        device = self.make_device(AristonEvoDevice)
        device.api.get_features_for_device.return_value = {"feature": True}
        device.api.get_velis_plant_data.return_value = {
            "state": "ready",
            VelisDeviceProperties.PROC_REQ_TEMP: 53,
        }
        device.api.get_velis_plant_settings.return_value = {
            MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF: True,
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE: 75,
        }
        device.get_features()
        device.update_state()
        self.assertTrue(device.custom_features["hasDhw"])
        self.assertTrue(device.features["dhwModeChangeable"])
        self.assertEqual(device.data, {"state": "ready", VelisDeviceProperties.PROC_REQ_TEMP: 53})
        self.assertTrue(device.water_anti_leg_value)
        self.assertEqual(device.proc_req_temp_value, 53)
        self.assertEqual(device.water_heater_maximum_setpoint_temperature, 75)
        self.assertEqual(device.water_heater_maximum_temperature, 75)
        self.assertEqual(device.water_heater_minimum_temperature, 40)
        self.assertEqual(device.water_heater_temperature_step, 1)
        self.assertEqual(device.water_heater_temperature_decimals, 0)
        self.assertEqual(device.water_heater_temperature_unit, "°C")
        device.set_power(False)
        self.assertFalse(device.data[VelisBaseDeviceProperties.ON])
        device.set_antilegionella(False)
        self.assertFalse(device.plant_settings[MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF])
        device.set_max_setpoint_temp(70)
        self.assertEqual(device.plant_settings[MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE], 70)

        device.api.async_get_features_for_device = AsyncMock(return_value={"async": True})
        device.api.async_get_velis_plant_data = AsyncMock(return_value={"state": "async"})
        device.api.async_get_velis_plant_settings = AsyncMock(return_value={
            MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF: False,
            MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE: 65,
        })
        device.api.async_set_velis_power = AsyncMock()
        device.api.async_set_velis_plant_setting = AsyncMock()

        async def update_and_set():
            await device.async_get_features()
            await device.async_update_state()
            await device.async_set_power(True)
            await device.async_set_antilegionella(True)
            await device.async_set_max_setpoint_temp(72)

        asyncio.run(update_and_set())
        self.assertEqual(device.features, {"async": True, "dhwModeChangeable": True})
        self.assertEqual(device.data, {"state": "async", VelisBaseDeviceProperties.ON: True})
        self.assertTrue(device.plant_settings[MedDeviceSettings.MED_ANTILEGIONELLA_ON_OFF])
        self.assertEqual(device.plant_settings[MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE], 72)
        device.api.async_set_velis_power.assert_awaited_once()
        self.assertEqual(device.water_heater_mode_operation_texts, [mode.name for mode in EvoPlantMode])
        for property_name in (
            "water_heater_maximum_setpoint_temperature_minimum",
            "water_heater_maximum_setpoint_temperature_maximum",
        ):
            with self.subTest(abstract_property=property_name):
                property_getter = getattr(AristonVelisDevice, property_name).fget
                with self.assertRaises(NotImplementedError):
                    property_getter(device)

    def test_lux_lux2_and_lydos_special_modes_and_power_option(self):
        lux = self.make_device(
            AristonLuxDevice,
            {
                EvoDeviceProperties.MODE: LuxPlantMode.BOOST.value,
                EvoDeviceProperties.REQ_TEMP: 52,
            },
        )
        lux.plant_settings[MedDeviceSettings.MED_MAX_SETPOINT_TEMPERATURE_MAX] = 78
        self.assertEqual(lux.water_heater_target_temperature, 78)
        self.assertEqual(lux.water_heater_mode, LuxPlantMode)
        lux.data[EvoDeviceProperties.MODE] = LuxPlantMode.MANUAL.value
        self.assertEqual(lux.water_heater_target_temperature, 52)
        lux.set_water_heater_operation_mode("BOOST")
        self.assertEqual(lux.data[EvoDeviceProperties.MODE], LuxPlantMode.BOOST.value)
        lux.api.async_set_evo_mode = AsyncMock()
        asyncio.run(lux.async_set_water_heater_operation_mode("PROGRAM"))
        self.assertEqual(lux.data[EvoDeviceProperties.MODE], LuxPlantMode.PROGRAM.value)
        lux.api.async_set_evo_mode.assert_awaited_once_with("gw-1", LuxPlantMode.PROGRAM)

        lux2 = self.make_device(AristonLux2Device)
        lux2.set_water_heater_power_option(True)
        self.assertTrue(lux2.water_heater_power_option_value)
        lux2.api.async_set_lux_power_option = AsyncMock()
        asyncio.run(lux2.async_set_water_heater_power_option(False))
        self.assertFalse(lux2.water_heater_power_option_value)
        lux2.api.async_set_lux_power_option.assert_awaited_once_with("gw-1", False)

        lydos = self.make_device(AristonLydosDevice)
        lydos.set_water_heater_operation_mode("BOOST")
        self.assertEqual(lydos.data[EvoDeviceProperties.MODE], LuxPlantMode.BOOST.value)
        lydos.api.async_set_evo_mode = AsyncMock()
        asyncio.run(lydos.async_set_water_heater_operation_mode("MANUAL"))
        self.assertEqual(lydos.data[EvoDeviceProperties.MODE], LuxPlantMode.MANUAL.value)

    def test_nuos_split_properties_sync_async_and_missing_state_defaults(self):
        device = self.make_device(
            AristonNuosSplitDevice,
            {
                NuosSplitProperties.WATER_TEMP: 43,
                NuosSplitProperties.COMFORT_TEMP: 55,
                NuosSplitProperties.REDUCED_TEMP: 40,
                NuosSplitProperties.BOOST_ON: True,
                NuosSplitProperties.OP_MODE: NuosSplitOperativeMode.COMFORT.value,
            },
        )
        device.plant_settings = {
            key: index for index, key in enumerate(
                (
                    SlpDeviceSettings.SLP_MAX_SETPOINT_TEMPERATURE_MIN,
                    SlpDeviceSettings.SLP_MAX_SETPOINT_TEMPERATURE_MAX,
                    SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE,
                    SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE_MIN,
                    SlpDeviceSettings.SLP_MIN_SETPOINT_TEMPERATURE_MAX,
                    SlpDeviceSettings.SLP_PRE_HEATING_ON_OFF,
                    SlpDeviceSettings.SLP_HEATING_RATE,
                ), 40
            )
        }
        self.assertEqual(device.water_heater_current_temperature, 43)
        self.assertEqual(device.water_heater_target_temperature, 55)
        self.assertEqual(device.water_heater_reduced_temperature, 40)
        self.assertEqual(device.water_heater_maximum_setpoint_temperature_minimum, 40)
        self.assertEqual(device.water_heater_maximum_setpoint_temperature_maximum, 41)
        self.assertEqual(device.water_heater_minimum_setpoint_temperature, 42)
        self.assertEqual(device.water_heater_minimum_setpoint_temperature_minimum, 43)
        self.assertEqual(device.water_heater_minimum_setpoint_temperature_maximum, 44)
        self.assertEqual(device.water_heater_preheating_on_off, 45)
        self.assertEqual(device.water_heater_heating_rate, 46)
        self.assertTrue(device.water_heater_boost)
        self.assertEqual(device.water_heater_mode_value, NuosSplitOperativeMode.COMFORT.value)
        self.assertEqual(device.consumption_type, "DhwHeatingPumpElec%2CDhwResistorElec")
        self.assertEqual(device.anti_legionella_on_off, SlpDeviceSettings.SLP_ANTILEGIONELLA_ON_OFF)
        self.assertEqual(device.max_setpoint_temp, SlpDeviceSettings.SLP_MAX_SETPOINT_TEMPERATURE)
        self.assertEqual(device.water_heater_mode, NuosSplitOperativeMode)

        device.set_water_heater_boost(False)
        device.set_water_heater_temperature(60)
        # The getter must reflect the requested target immediately, without
        # waiting for the next cloud refresh (regression: setter used to write
        # procReqTemp while the getter reads comfortTemp).
        self.assertEqual(device.water_heater_target_temperature, 60)
        self.assertEqual(device.data[NuosSplitProperties.COMFORT_TEMP], 60)
        self.assertNotIn(NuosSplitProperties.PROC_REQ_TEMP, device.data)
        device.set_water_heater_reduced_temperature(42)
        device.set_water_heater_operation_mode("FAST")
        # The getter must reflect the requested mode immediately (regression:
        # setter used to write `mode` while the getter reads `opMode`).
        self.assertEqual(device.water_heater_mode_value, NuosSplitOperativeMode.FAST.value)
        self.assertNotIn(NuosSplitProperties.MODE, device.data)
        device.set_min_setpoint_temp(35)
        device.set_preheating(True)
        device.set_heating_rate(5)
        self.assertEqual(device.data[NuosSplitProperties.COMFORT_TEMP], 43)
        self.assertEqual(device.data[NuosSplitProperties.REDUCED_TEMP], 42)
        self.assertEqual(device.data[NuosSplitProperties.OP_MODE], NuosSplitOperativeMode.FAST.value)
        device.api.set_nuos_temperature.assert_called_with("gw-1", 43, 42, 60, 40)
        device.api.set_velis_plant_setting.assert_called()

        device.api.async_set_nous_boost = AsyncMock()
        device.api.async_set_nuos_temperature = AsyncMock()
        device.api.async_set_nuos_mode = AsyncMock()
        device.api.async_set_velis_plant_setting = AsyncMock()

        async def set_values():
            await device.async_set_water_heater_boost(True)
            await device.async_set_water_heater_temperature(62)
            self.assertEqual(device.water_heater_target_temperature, 62)
            self.assertEqual(device.data[NuosSplitProperties.COMFORT_TEMP], 62)
            self.assertNotIn(NuosSplitProperties.PROC_REQ_TEMP, device.data)
            await device.async_set_water_heater_reduced_temperature(39)
            await device.async_set_water_heater_operation_mode("GREEN")
            await device.async_set_min_setpoint_temp(36)
            await device.async_set_preheating(False)
            await device.async_set_heating_rate(4)

        asyncio.run(set_values())
        self.assertTrue(device.data[NuosSplitProperties.BOOST_ON])
        self.assertEqual(device.data[NuosSplitProperties.OP_MODE], NuosSplitOperativeMode.GREEN.value)
        self.assertEqual(device.water_heater_mode_value, NuosSplitOperativeMode.GREEN.value)
        self.assertNotIn(NuosSplitProperties.MODE, device.data)
        self.assertEqual(device.plant_settings[SlpDeviceSettings.SLP_HEATING_RATE], 4)
        self.assertEqual(device.api.async_set_velis_plant_setting.await_count, 3)

        missing = self.make_device(AristonNuosSplitDevice)
        missing.api.get_velis_plant_data.return_value = {}
        missing.set_water_heater_reduced_temperature(38)
        self.assertEqual(missing.api.set_nuos_temperature.call_args.args[1:3], (0, 38))

        async_missing = self.make_device(AristonNuosSplitDevice)
        async_missing.api.async_get_velis_plant_data = AsyncMock(return_value={})
        async_missing.api.async_set_nuos_temperature = AsyncMock()
        asyncio.run(async_missing.async_set_water_heater_reduced_temperature(37))
        self.assertEqual(
            async_missing.api.async_set_nuos_temperature.await_args.args[1:3],
            (40.0, 37),
        )

        missing_temperature = self.make_device(AristonNuosSplitDevice)
        missing_temperature.api.get_velis_plant_data.return_value = {}
        missing_temperature.set_water_heater_temperature(59)
        self.assertEqual(
            missing_temperature.api.set_nuos_temperature.call_args.args[1:3],
            (59, 0),
        )

        async_missing_temperature = self.make_device(AristonNuosSplitDevice)
        async_missing_temperature.api.async_get_velis_plant_data = AsyncMock(return_value={})
        async_missing_temperature.api.async_set_nuos_temperature = AsyncMock()
        asyncio.run(async_missing_temperature.async_set_water_heater_temperature(61))
        self.assertEqual(
            async_missing_temperature.api.async_set_nuos_temperature.await_args.args[1:3],
            (61, 0),
        )

    def test_nuos_split_holiday_state_and_sync_async_setters(self):
        holiday_end_date = "2026-12-31T00:00:00"
        scheduled = self.make_device(
            AristonNuosSplitDevice,
            {NuosSplitProperties.HOLIDAY_UNTIL: holiday_end_date},
        )
        self.assertEqual(scheduled.holiday_end_date, holiday_end_date)
        self.assertTrue(scheduled.holiday_active)

        cleared = self.make_device(
            AristonNuosSplitDevice,
            {NuosSplitProperties.HOLIDAY_UNTIL: None},
        )
        self.assertIsNone(cleared.holiday_end_date)
        self.assertFalse(cleared.holiday_active)

        missing = self.make_device(AristonNuosSplitDevice)
        self.assertIsNone(missing.holiday_end_date)
        self.assertFalse(missing.holiday_active)

        device = self.make_device(AristonNuosSplitDevice)
        device.set_holiday(date(2026, 12, 31))
        self.assertEqual(device.holiday_end_date, holiday_end_date)
        self.assertTrue(device.holiday_active)
        device.set_holiday(None)
        self.assertIsNone(device.holiday_end_date)
        self.assertFalse(device.holiday_active)
        device.api.set_velis_slp_holiday.assert_has_calls(
            [call("gw-1", holiday_end_date), call("gw-1", None)]
        )

        async_device = self.make_device(AristonNuosSplitDevice)
        async_device.api.async_set_velis_slp_holiday = AsyncMock()

        async def set_holidays():
            await async_device.async_set_holiday(date(2026, 12, 31))
            self.assertEqual(async_device.holiday_end_date, holiday_end_date)
            self.assertTrue(async_device.holiday_active)
            await async_device.async_set_holiday(None)

        asyncio.run(set_holidays())
        self.assertIsNone(async_device.holiday_end_date)
        self.assertFalse(async_device.holiday_active)
        self.assertEqual(
            async_device.api.async_set_velis_slp_holiday.await_args_list,
            [call("gw-1", holiday_end_date), call("gw-1", None)],
        )

    def test_nuos_split_green_plus_mode_is_exposed_and_settable(self):
        device = self.make_device(AristonNuosSplitDevice)
        self.assertEqual(NuosSplitOperativeMode.GREEN_PLUS.value, 6)
        self.assertIn(
            NuosSplitOperativeMode.GREEN_PLUS.value,
            device.water_heater_mode_options,
        )
        self.assertIn("GREEN_PLUS", device.water_heater_mode_operation_texts)

        device.set_water_heater_operation_mode("GREEN_PLUS")
        self.assertEqual(
            device.data[NuosSplitProperties.OP_MODE], NuosSplitOperativeMode.GREEN_PLUS.value
        )
        self.assertEqual(
            device.water_heater_mode_value, NuosSplitOperativeMode.GREEN_PLUS.value
        )
        device.api.set_nuos_mode.assert_called_once_with(
            "gw-1", NuosSplitOperativeMode.GREEN_PLUS
        )

        device.api.async_set_nuos_mode = AsyncMock()
        asyncio.run(device.async_set_water_heater_operation_mode("GREEN_PLUS"))
        self.assertEqual(
            device.data[NuosSplitProperties.OP_MODE], NuosSplitOperativeMode.GREEN_PLUS.value
        )
        self.assertEqual(
            device.water_heater_mode_value, NuosSplitOperativeMode.GREEN_PLUS.value
        )
        device.api.async_set_nuos_mode.assert_awaited_once_with(
            "gw-1", NuosSplitOperativeMode.GREEN_PLUS
        )

    def test_lydos_hybrid_settings_accessors_and_all_commands(self):
        setting_keys = (
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MIN,
            SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE_MAX,
            SeDeviceSettings.SE_PERMANENT_BOOST_ON_OFF,
            SeDeviceSettings.SE_ANTI_COOLING_ON_OFF,
            SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE,
            SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE_MAX,
            SeDeviceSettings.SE_ANTI_COOLING_TEMPERATURE_MIN,
            SeDeviceSettings.SE_NIGHT_MODE_ON_OFF,
            SeDeviceSettings.SE_NIGHT_BEGIN_AS_MINUTES,
            SeDeviceSettings.SE_NIGHT_BEGIN_MAX_AS_MINUTES,
            SeDeviceSettings.SE_NIGHT_BEGIN_MIN_AS_MINUTES,
            SeDeviceSettings.SE_NIGHT_END_AS_MINUTES,
            SeDeviceSettings.SE_NIGHT_END_MAX_AS_MINUTES,
            SeDeviceSettings.SE_NIGHT_END_MIN_AS_MINUTES,
            SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF,
        )
        device = self.make_device(AristonLydosHybridDevice)
        device.plant_settings = {key: 1 for key in setting_keys}
        device.consumptions_sequences = []
        for index, property_name in enumerate(
            (
                "water_heater_maximum_setpoint_temperature_minimum",
                "water_heater_maximum_setpoint_temperature_maximum",
                "permanent_boost_value",
                "anti_cooling_value",
                "anti_cooling_temperature_value",
                "anti_cooling_temperature_maximum",
                "anti_cooling_temperature_minimum",
                "night_mode_value",
                "night_mode_begin_as_minutes_value",
                "night_mode_begin_max_as_minutes_value",
                "night_mode_begin_min_as_minutes_value",
                "night_mode_end_as_minutes_value",
                "night_mode_end_max_as_minutes_value",
                "night_mode_end_min_as_minutes_value",
            )
        ):
            with self.subTest(property_name=property_name):
                self.assertEqual(getattr(device, property_name), 1)
        self.assertEqual(device.water_heater_mode, LydosPlantMode)
        self.assertEqual(device.plant_data.value, "sePlantData")
        self.assertEqual(device.anti_legionella_on_off, SeDeviceSettings.SE_ANTILEGIONELLA_ON_OFF)
        self.assertEqual(device.consumption_type, "DhwHeatingPumpElec%2CDhwResistorElec")
        self.assertEqual(device.max_setpoint_temp, SeDeviceSettings.SE_MAX_SETPOINT_TEMPERATURE)
        device.consumptions_sequences = [{
            "k": ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY.value,
            "p": ConsumptionTimeInterval.LAST_DAY.value,
            "v": [3, 8],
        }]
        self.assertEqual(device.electric_consumption_for_water_last_two_hours, 8)

        operations = (
            ("set_water_heater_operation_mode", "async_set_water_heater_operation_mode", "BOOST"),
            ("set_water_heater_temperature", "async_set_water_heater_temperature", 55),
            ("set_permanent_boost_value", "async_set_permanent_boost_value", False),
            ("set_anti_cooling_value", "async_set_anti_cooling_value", False),
            ("set_cooling_temperature_value", "async_set_cooling_temperature_value", 12),
            ("set_night_mode_value", "async_set_night_mode_value", False),
            ("set_night_mode_begin_as_minutes_value", "async_set_night_mode_begin_as_minutes_value", 450),
            ("set_night_mode_end_as_minutes_value", "async_set_night_mode_end_as_minutes_value", 390),
        )
        for sync_name, async_name, value in operations:
            with self.subTest(command=sync_name):
                getattr(device, sync_name)(value)
                if sync_name == "set_water_heater_operation_mode":
                    self.assertTrue(device.api.set_lydos_mode.called)
                elif sync_name == "set_water_heater_temperature":
                    self.assertTrue(device.api.set_lydos_temperature.called)
                else:
                    self.assertTrue(device.api.set_velis_plant_setting.called)

        async_methods = (
            "async_set_lydos_mode",
            "async_set_lydos_temperature",
            "async_set_velis_plant_setting",
        )
        for method_name in async_methods:
            setattr(device.api, method_name, AsyncMock())

        async def set_values():
            for _, async_name, value in operations:
                await getattr(device, async_name)(value)

        asyncio.run(set_values())
        self.assertEqual(device.data[LydosDeviceProperties.MODE], LydosPlantMode.BOOST.value)
        self.assertEqual(device.data[LydosDeviceProperties.REQ_TEMP], 55)
        self.assertEqual(device.api.async_set_velis_plant_setting.await_count, 6)


if __name__ == "__main__":
    unittest.main()
