"""Tests for cloud discovery and device selection."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

import ariston
from ariston import Ariston
from ariston.bsb_device import AristonBsbDevice
from ariston.const import DeviceAttribute, SystemType, VelisDeviceAttribute, WheType
from ariston.evo_device import AristonEvoDevice
from ariston.evo_one_device import AristonEvoOneDevice
from ariston.galevo_device import AristonGalevoDevice
from ariston.lux2_device import AristonLux2Device
from ariston.lux_device import AristonLuxDevice
from ariston.lydos_device import AristonLydosDevice
from ariston.lydos_hybrid_device import AristonLydosHybridDevice
from ariston.nuos_split_device import AristonNuosSplitDevice


class DeviceSelectionTests(unittest.TestCase):
    def test_selects_device_class_for_each_supported_system(self):
        cases = [
            (SystemType.GALEVO.value, None, AristonGalevoDevice),
            (SystemType.BSB.value, None, AristonBsbDevice),
            (SystemType.VELIS.value, WheType.Evo.value, AristonEvoOneDevice),
            (
                SystemType.VELIS.value,
                WheType.LydosHybrid.value,
                AristonLydosHybridDevice,
            ),
            (SystemType.VELIS.value, WheType.Lydos.value, AristonLydosDevice),
            (
                SystemType.VELIS.value,
                WheType.NuosSplit.value,
                AristonNuosSplitDevice,
            ),
            (SystemType.VELIS.value, WheType.Andris2.value, AristonEvoDevice),
            (SystemType.VELIS.value, WheType.Evo2.value, AristonEvoDevice),
            (SystemType.VELIS.value, WheType.Lux2.value, AristonLux2Device),
            (SystemType.VELIS.value, WheType.Lux.value, AristonLuxDevice),
        ]

        for system, whe_type, expected_class in cases:
            with self.subTest(system=system, whe_type=whe_type):
                attributes = {
                    DeviceAttribute.GW: "gateway",
                    DeviceAttribute.SYS: system,
                }
                if whe_type is not None:
                    attributes[VelisDeviceAttribute.WHE_TYPE] = whe_type

                with patch("ariston._connect", return_value=Mock()), patch(
                    "ariston._discover", return_value=[attributes]
                ):
                    device = ariston.hello("user", "password", "gateway")

                self.assertIsInstance(device, expected_class)

    def test_returns_none_for_unknown_gateway_or_unsupported_device(self):
        api = Mock()

        with patch("ariston._connect", return_value=api):
            with patch("ariston._discover", return_value=[]):
                with self.assertLogs("ariston", level="ERROR"):
                    self.assertIsNone(ariston.hello("user", "password", "missing"))

            unsupported_devices = [
                {DeviceAttribute.GW: "gateway", DeviceAttribute.SYS: 999},
                {
                    DeviceAttribute.GW: "gateway",
                    DeviceAttribute.SYS: SystemType.VELIS.value,
                    VelisDeviceAttribute.WHE_TYPE: 999,
                },
            ]
            for attributes in unsupported_devices:
                with patch("ariston._discover", return_value=[attributes]):
                    with self.assertLogs("ariston", level="ERROR"):
                        self.assertIsNone(
                            ariston.hello("user", "password", "gateway")
                        )

    def test_discovery_combines_remote_and_velis_devices(self):
        api = Mock()
        api.get_detailed_devices.return_value = [{"gw": "remote"}]
        api.get_detailed_velis_devices.return_value = [{"gw": "velis"}]

        with patch("ariston._connect", return_value=api):
            devices = ariston.discover("user", "password")

        self.assertEqual(devices, [{"gw": "remote"}, {"gw": "velis"}])

    def test_async_discovery_combines_both_device_sources(self):
        api = Mock()
        api.async_get_detailed_devices = AsyncMock(return_value=[{"gw": "remote"}])
        api.async_get_detailed_velis_devices = AsyncMock(
            return_value=[{"gw": "velis"}]
        )

        with patch("ariston._async_connect", new=AsyncMock(return_value=api)):
            devices = asyncio.run(ariston.async_discover("user", "password"))

        self.assertEqual(devices, [{"gw": "remote"}, {"gw": "velis"}])

    def test_async_client_discovers_devices_and_selects_requested_device(self):
        client = Ariston()
        client.api = Mock()
        client.api.async_get_detailed_devices = AsyncMock(return_value=[])
        client.api.async_get_detailed_velis_devices = AsyncMock(
            return_value=[
                {
                    DeviceAttribute.GW: "gateway",
                    DeviceAttribute.SYS: SystemType.VELIS.value,
                    VelisDeviceAttribute.WHE_TYPE: WheType.Evo.value,
                }
            ]
        )

        device = asyncio.run(client.async_hello("gateway"))

        self.assertIsInstance(device, AristonEvoOneDevice)
        self.assertEqual(client.cloud_devices[0][DeviceAttribute.GW], "gateway")


if __name__ == "__main__":
    unittest.main()
