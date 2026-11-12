"""Contracts shared by every Ariston device implementation."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

from ariston.base_device import AristonBaseDevice
from ariston.const import (
    ConsumptionTimeInterval,
    ConsumptionType,
    CustomDeviceFeatures,
    DeviceAttribute,
    DeviceFeatures,
    GalevoDeviceAttribute,
    SystemType,
    VelisDeviceAttribute,
    WheType,
)
from ariston.device import AristonDevice
from ariston.evo_one_device import AristonEvoOneDevice


class AristonBaseDeviceTests(unittest.TestCase):
    def make_device(self, attributes=None):
        return AristonEvoOneDevice(Mock(), attributes or {DeviceAttribute.GW: "gw-1"})

    def test_metadata_properties_return_values_and_defaults(self):
        device = self.make_device(
            {
                DeviceAttribute.GW: "gateway-1",
                DeviceAttribute.SYS: SystemType.BSB.value,
                DeviceAttribute.NAME: "Living room",
                DeviceAttribute.SN: "serial-1",
                DeviceAttribute.HPMP_SYS: True,
                VelisDeviceAttribute.WHE_TYPE: WheType.Evo.value,
                VelisDeviceAttribute.WHE_MODEL_TYPE: 7,
                GalevoDeviceAttribute.FW_VER: "1.2.3",
            }
        )
        device.features = {
            DeviceFeatures.HAS_METERING: True,
            DeviceFeatures.DHW_MODE_CHANGEABLE: False,
        }
        device.custom_features[CustomDeviceFeatures.HAS_DHW] = True
        errors = [{"code": 1}]
        device.bus_errors_list = errors

        self.assertEqual(device.system_type, SystemType.BSB)
        self.assertEqual(device.whe_type, WheType.Evo)
        self.assertEqual(device.whe_model_type, 7)
        self.assertEqual(device.gateway, "gateway-1")
        self.assertTrue(device.has_metering)
        self.assertEqual(device.name, "Living room")
        self.assertTrue(device.has_dhw)
        self.assertFalse(device.dhw_mode_changeable)
        self.assertEqual(device.serial_number, "serial-1")
        self.assertEqual(device.firmware_version, "1.2.3")
        self.assertIs(device.bus_errors, errors)
        self.assertTrue(device.hpmp_sys)

        defaults = self.make_device()
        self.assertEqual(defaults.system_type, SystemType.UNKNOWN)
        self.assertEqual(defaults.whe_type, WheType.Unknown)
        self.assertEqual(defaults.whe_model_type, 0)
        self.assertEqual(defaults.gateway, "gw-1")
        self.assertIsNone(defaults.has_metering)
        self.assertIsNone(defaults.name)
        self.assertIsNone(defaults.has_dhw)
        self.assertIsNone(defaults.dhw_mode_changeable)
        self.assertIsNone(defaults.serial_number)
        self.assertIsNone(defaults.firmware_version)
        self.assertEqual(defaults.bus_errors, [])
        self.assertIsNone(defaults.hpmp_sys)

    def test_sync_and_async_feature_loading(self):
        device = self.make_device()
        expected = {DeviceFeatures.HAS_METERING: True}
        device.api.get_features_for_device.return_value = expected
        AristonBaseDevice.get_features(device)
        device.api.get_features_for_device.assert_called_once_with("gw-1")
        self.assertEqual(device.features, expected)

        device.api.async_get_features_for_device = AsyncMock(return_value=None)
        asyncio.run(AristonBaseDevice.async_get_features(device))
        device.api.async_get_features_for_device.assert_awaited_once_with("gw-1")
        self.assertEqual(device.features, expected)

        device.api.async_get_features_for_device = AsyncMock(return_value={"new": 1})
        asyncio.run(AristonBaseDevice.async_get_features(device))
        self.assertEqual(device.features, {"new": 1})

    def test_consumption_accessors_select_the_last_sample_for_each_type(self):
        device = self.make_device()
        interval = ConsumptionTimeInterval.LAST_DAY
        device.consumptions_sequences = [
            {"k": kind.value, "p": interval.value, "v": [index, index + 1]}
            for index, kind in enumerate(ConsumptionType)
        ]

        properties = (
            "central_heating_total_energy_consumption",
            "domestic_hot_water_total_energy_consumption",
            "central_heating_gas_consumption",
            "domestic_hot_water_heating_pump_electricity_consumption",
            "domestic_hot_water_resistor_electricity_consumption",
            "domestic_hot_water_gas_consumption",
            "central_heating_electricity_consumption",
            "domestic_hot_water_electricity_consumption",
        )
        for property_name in properties:
            with self.subTest(property_name=property_name):
                self.assertIsNotNone(getattr(device, property_name))

        self.assertIsNone(
            device._get_consumption_sequence_last_value(
                ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY,
                ConsumptionTimeInterval.LAST_MONTH,
            )
        )

    def test_energy_feature_flags_and_change_timestamp(self):
        device = self.make_device()
        new_sequences = [
            {
                "k": ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY.value,
                "p": ConsumptionTimeInterval.LAST_DAY.value,
                "v": [2.5],
            }
        ]
        device.consumptions_sequences = new_sequences
        device._update_energy(
            [{"k": "old", "p": "old", "v": [1]}]
        )

        self.assertTrue(
            device.custom_features[
                ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY.name
            ]
        )
        self.assertTrue(
            all(
                device.custom_features[kind.name]
                is (kind is ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY)
                for kind in ConsumptionType
            )
        )
        self.assertGreater(
            device.consumption_sequence_last_changed_utc,
            datetime.now(timezone.utc) - timedelta(days=1),
        )

        timestamp = device.consumption_sequence_last_changed_utc
        device._update_energy(new_sequences)
        self.assertEqual(device.consumption_sequence_last_changed_utc, timestamp)
        device._update_energy(None)
        device._update_energy([])

    def test_sync_and_async_energy_and_bus_error_updates(self):
        device = self.make_device()
        sequences = [
            {
                "k": ConsumptionType.CENTRAL_HEATING_GAS.value,
                "p": ConsumptionTimeInterval.LAST_DAY.value,
                "v": [1],
            }
        ]
        device.api.get_consumptions_sequences.return_value = sequences
        device.update_energy()
        device.api.get_consumptions_sequences.assert_called_once_with("gw-1", "Dhw")
        self.assertEqual(device.consumptions_sequences, sequences)

        device.api.async_get_consumptions_sequences = AsyncMock(return_value=[])
        asyncio.run(device.async_update_energy())
        device.api.async_get_consumptions_sequences.assert_awaited_once_with("gw-1", "Dhw")
        self.assertEqual(device.consumptions_sequences, [])

        errors = [{"code": "sync"}]
        device.api.get_bus_errors.return_value = errors
        device.get_bus_errors()
        self.assertEqual(device.bus_errors, errors)
        device.api.async_get_bus_errors = AsyncMock(return_value=[{"code": "async"}])
        asyncio.run(device.async_get_bus_errors())
        self.assertEqual(device.bus_errors, [{"code": "async"}])

    def test_feature_availability_checks_system_whe_and_feature_sources(self):
        device = self.make_device(
            {
                DeviceAttribute.GW: "gw-1",
                DeviceAttribute.SYS: SystemType.VELIS.value,
                VelisDeviceAttribute.WHE_TYPE: WheType.Evo.value,
                "from_attribute": True,
            }
        )
        device.features["from_feature"] = True
        device.custom_features["from_custom"] = True

        self.assertTrue(device.are_device_features_available(None, None, None))
        self.assertTrue(
            device.are_device_features_available(
                ["from_feature", "from_custom", "from_attribute"],
                [SystemType.VELIS],
                [WheType.Evo],
            )
        )
        self.assertFalse(
            device.are_device_features_available(None, [SystemType.BSB], None)
        )
        self.assertFalse(
            device.are_device_features_available(None, None, [WheType.Lux])
        )
        self.assertFalse(
            device.are_device_features_available(["missing"], None, None)
        )

    def test_abstract_device_contracts_raise_not_implemented(self):
        device = self.make_device()
        base_properties = (
            "water_heater_current_temperature",
            "water_heater_mode_operation_texts",
            "water_heater_mode_options",
            "water_heater_mode_value",
        )
        for property_name in base_properties:
            with self.subTest(property_name=property_name):
                property_getter = getattr(AristonBaseDevice, property_name).fget
                with self.assertRaises(NotImplementedError):
                    property_getter(device)

        for method_name, arguments in (
            ("update_state", ()),
            ("set_water_heater_operation_mode", ("AUTO",)),
        ):
            with self.subTest(method_name=method_name):
                with self.assertRaises(NotImplementedError):
                    getattr(AristonBaseDevice, method_name)(device, *arguments)

        for method_name, arguments in (
            ("async_update_state", ()),
            ("async_set_water_heater_operation_mode", ("AUTO",)),
        ):
            with self.subTest(method_name=method_name):
                with self.assertRaises(NotImplementedError):
                    asyncio.run(getattr(AristonBaseDevice, method_name)(device, *arguments))

        device_properties = (
            "water_heater_temperature_decimals",
            "water_heater_temperature_unit",
            "water_heater_temperature_step",
            "water_heater_minimum_temperature",
            "water_heater_target_temperature",
            "water_heater_maximum_temperature",
        )
        for property_name in device_properties:
            with self.subTest(property_name=property_name):
                property_getter = getattr(AristonDevice, property_name).fget
                with self.assertRaises(NotImplementedError):
                    property_getter(device)

        for method_name in (
            "set_water_heater_temperature",
            "async_set_water_heater_temperature",
        ):
            with self.subTest(method_name=method_name):
                call = getattr(AristonDevice, method_name)
                with self.assertRaises(NotImplementedError):
                    result = call(device, 50)
                    if method_name.startswith("async_"):
                        asyncio.run(result)


if __name__ == "__main__":
    unittest.main()
