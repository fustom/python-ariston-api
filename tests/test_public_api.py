"""Tests for the synchronous and asynchronous public discovery helpers."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

import ariston
from ariston.const import DeviceAttribute, SystemType, VelisDeviceAttribute, WheType
from ariston.evo_device import AristonEvoDevice
from ariston.evo_one_device import AristonEvoOneDevice
from ariston.galevo_device import AristonGalevoDevice
from ariston.lux2_device import AristonLux2Device
from ariston.lux_device import AristonLuxDevice
from ariston.lydos_device import AristonLydosDevice
from ariston.lydos_hybrid_device import AristonLydosHybridDevice
from ariston.nuos_split_device import AristonNuosSplitDevice
from ariston.bsb_device import AristonBsbDevice


class AristonPublicApiTests(unittest.TestCase):
    def test_device_factory_selects_each_supported_system_and_water_heater(self):
        api = Mock()
        self.assertIsNone(ariston._get_device([], api, "missing"))

        galevo = ariston._get_device(
            [{DeviceAttribute.GW: "gw-1", DeviceAttribute.SYS: SystemType.GALEVO.value}],
            api,
            "gw-1",
            False,
            "pt-PT",
        )
        self.assertIsInstance(galevo, AristonGalevoDevice)
        self.assertEqual(galevo.umsys, "us")
        self.assertEqual(galevo.language_tag, "pt-PT")

        bsb = ariston._get_device(
            [{DeviceAttribute.GW: "gw-2", DeviceAttribute.SYS: SystemType.BSB.value}],
            api,
            "gw-2",
        )
        self.assertIsInstance(bsb, AristonBsbDevice)

        expected_types = {
            WheType.Evo: AristonEvoOneDevice,
            WheType.LydosHybrid: AristonLydosHybridDevice,
            WheType.Lydos: AristonLydosDevice,
            WheType.NuosSplit: AristonNuosSplitDevice,
            WheType.Andris2: AristonEvoDevice,
            WheType.Evo2: AristonEvoDevice,
            WheType.Lux2: AristonLux2Device,
            WheType.Lux: AristonLuxDevice,
        }
        for whe_type, expected_class in expected_types.items():
            with self.subTest(whe_type=whe_type):
                device = ariston._get_device(
                    [
                        {
                            DeviceAttribute.GW: "velis-1",
                            DeviceAttribute.SYS: SystemType.VELIS.value,
                            VelisDeviceAttribute.WHE_TYPE: whe_type.value,
                        }
                    ],
                    api,
                    "velis-1",
                )
                self.assertIsInstance(device, expected_class)

        unsupported_type = ariston._get_device(
            [
                {
                    DeviceAttribute.GW: "bad-velis",
                    DeviceAttribute.SYS: SystemType.VELIS.value,
                    VelisDeviceAttribute.WHE_TYPE: 999,
                }
            ],
            api,
            "bad-velis",
        )
        self.assertIsNone(unsupported_type)
        unsupported_system = ariston._get_device(
            [{DeviceAttribute.GW: "unknown", DeviceAttribute.SYS: -1}], api, "unknown"
        )
        self.assertIsNone(unsupported_system)

    def test_sync_connect_discover_and_hello_helpers(self):
        api = Mock()
        api.get_detailed_devices.return_value = [{"gw": "remote"}]
        api.get_detailed_velis_devices.return_value = [{"gw": "velis"}]
        with patch.object(ariston, "AristonAPI", return_value=api) as constructor:
            connected_api = ariston._connect("user", "secret", "https://api.test/", "agent")
        constructor.assert_called_once_with("user", "secret", "https://api.test/", "agent")
        api.connect.assert_called_once_with()
        self.assertIs(connected_api, api)

        self.assertEqual(ariston._discover(api), [{"gw": "remote"}, {"gw": "velis"}])
        api.get_detailed_devices.assert_called_once_with()
        api.get_detailed_velis_devices.assert_called_once_with()

        with patch.object(ariston, "_connect", return_value=api) as connect:
            self.assertEqual(ariston.discover("user", "secret", "https://api.test/"), [{"gw": "remote"}, {"gw": "velis"}])
        connect.assert_called_once_with("user", "secret", "https://api.test/")

        with patch.object(ariston, "_connect", return_value=api), patch.object(
            ariston, "_discover", return_value=[
                {DeviceAttribute.GW: "gw-1", DeviceAttribute.SYS: SystemType.BSB.value}
            ]
        ):
            device = ariston.hello("user", "secret", "gw-1", api_url="https://api.test/")
        self.assertIsInstance(device, AristonBsbDevice)

    def test_async_facade_and_discovery_helpers(self):
        api = Mock()
        api.async_connect = AsyncMock(return_value=True)
        api.async_get_detailed_devices = AsyncMock(return_value=[{"gw": "remote"}])
        api.async_get_detailed_velis_devices = AsyncMock(return_value=[{"gw": "velis"}])

        async def exercise_helpers():
            connected = await ariston._async_connect("user", "secret")
            self.assertIs(connected, api)
            self.assertEqual(await ariston._async_discover(api), [{"gw": "remote"}, {"gw": "velis"}])
            self.assertEqual(await ariston.async_discover("user", "secret"), [{"gw": "remote"}, {"gw": "velis"}])

        with patch.object(ariston, "AristonAPI", return_value=api):
            asyncio.run(exercise_helpers())
        self.assertGreaterEqual(api.async_connect.await_count, 2)

        failed_api = Mock()
        failed_api.async_connect = AsyncMock(return_value=False)

        async def assert_failed_connect():
            with self.assertRaises(ariston.ConnectionException):
                await ariston._async_connect("user", "wrong")

        with patch.object(ariston, "AristonAPI", return_value=failed_api):
            asyncio.run(assert_failed_connect())

        facade = ariston.Ariston()
        self.assertIsNone(facade.api)
        self.assertEqual(facade.cloud_devices, [])
        self.assertEqual(asyncio.run(facade.async_discover()), [])
        self.assertIsNone(asyncio.run(facade.async_hello("gw-1")))

        facade.api = api
        api.async_connect = AsyncMock(return_value=True)
        api.async_get_detailed_devices = AsyncMock(return_value=[])
        api.async_get_detailed_velis_devices = AsyncMock(return_value=[])
        api.async_get_features_for_device = AsyncMock(return_value=None)

        async def facade_connect_discover():
            self.assertTrue(await facade.async_connect("user", "secret"))
            self.assertEqual(await facade.async_discover(), [])
            self.assertIsNone(await facade.async_hello("missing"))

        with patch.object(ariston, "AristonAPI", return_value=api):
            asyncio.run(facade_connect_discover())

    def test_async_hello_builds_selected_device(self):
        api = Mock()
        api.async_connect = AsyncMock(return_value=True)
        api.async_get_detailed_devices = AsyncMock(return_value=[])
        api.async_get_detailed_velis_devices = AsyncMock(
            return_value=[
                {
                    DeviceAttribute.GW: "gw-1",
                    DeviceAttribute.SYS: SystemType.VELIS.value,
                    VelisDeviceAttribute.WHE_TYPE: WheType.Evo.value,
                }
            ]
        )

        async def run():
            return await ariston.async_hello("user", "secret", "gw-1")

        with patch.object(ariston, "AristonAPI", return_value=api):
            device = asyncio.run(run())
        self.assertIsInstance(device, AristonEvoOneDevice)


if __name__ == "__main__":
    unittest.main()
