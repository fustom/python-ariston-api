"""Tests for device state and command behavior."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from ariston.ariston_api import ConnectionException
from ariston.const import (
    ConsumptionTimeInterval,
    ConsumptionType,
    EvoOneDeviceProperties,
    PlantData,
    VelisPlantMode,
)
from ariston.evo_one_device import AristonEvoOneDevice


class AristonEvoOneDeviceTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock()
        self.device = AristonEvoOneDevice(self.api, {"gw": "gateway-1"})

    def test_properties_read_values_from_latest_state(self):
        self.device.data = {
            EvoOneDeviceProperties.TEMP: 48.5,
            EvoOneDeviceProperties.MODE: VelisPlantMode.NIGHT.value,
            EvoOneDeviceProperties.STATE: True,
            EvoOneDeviceProperties.RM_TM: "02:45:00",
        }

        self.assertEqual(self.device.water_heater_current_temperature, 48.5)
        self.assertEqual(self.device.water_heater_current_mode_text, "NIGHT")
        self.assertTrue(self.device.is_heating)
        self.assertEqual(self.device.rm_tm_in_minutes, 165)

    def test_invalid_mode_value_has_unknown_text(self):
        self.device.data[EvoOneDeviceProperties.MODE] = 999

        self.assertEqual(self.device.water_heater_current_mode_text, "UNKNOWN")

    def test_sync_mode_command_updates_state_after_api_success(self):
        self.device.set_water_heater_operation_mode("PROGRAM")

        self.api.set_evo_mode.assert_called_once_with(
            "gateway-1", VelisPlantMode.PROGRAM
        )
        self.assertEqual(
            self.device.water_heater_mode_value,
            VelisPlantMode.PROGRAM.value,
        )

    def test_sync_mode_command_leaves_state_unchanged_when_api_fails(self):
        self.device.data[EvoOneDeviceProperties.MODE] = VelisPlantMode.NIGHT.value
        self.api.set_evo_mode.side_effect = ConnectionException("offline")

        with self.assertRaises(ConnectionException):
            self.device.set_water_heater_operation_mode("PROGRAM")

        self.assertEqual(
            self.device.water_heater_mode_value,
            VelisPlantMode.NIGHT.value,
        )

    def test_async_mode_command_updates_state_after_api_success(self):
        self.api.async_set_evo_mode = AsyncMock()

        asyncio.run(self.device.async_set_water_heater_operation_mode("PROGRAM"))

        self.api.async_set_evo_mode.assert_awaited_once_with(
            "gateway-1", VelisPlantMode.PROGRAM
        )
        self.assertEqual(
            self.device.water_heater_mode_value,
            VelisPlantMode.PROGRAM.value,
        )

    def test_async_state_refresh_replaces_cached_state(self):
        self.api.async_get_velis_plant_data = AsyncMock(
            return_value={EvoOneDeviceProperties.TEMP: 51.0}
        )

        asyncio.run(self.device.async_update_state())

        self.api.async_get_velis_plant_data.assert_awaited_once_with(
            PlantData.PD, "gateway-1"
        )
        self.assertEqual(
            self.device.data,
            {EvoOneDeviceProperties.TEMP: 51.0},
        )

    def test_energy_value_uses_last_sample_for_requested_interval(self):
        self.device.consumptions_sequences = [
            {
                "k": ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY.value,
                "p": ConsumptionTimeInterval.LAST_DAY.value,
                "v": [0.6, 1.2],
            }
        ]

        self.assertEqual(self.device.domestic_hot_water_electricity_consumption, 1.2)
        self.assertIsNone(self.device.central_heating_total_energy_consumption)


if __name__ == "__main__":
    unittest.main()
