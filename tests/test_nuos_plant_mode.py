"""Unit tests for the Nuos Split plant mode (Manual / Program) via R2."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from ariston.ariston_api import AristonAPI, ConnectionException
from ariston.const import NuosSplitOperativeMode, NuosSplitPlantMode
from ariston.nuos_split_device import AristonNuosSplitDevice

PLANT = {
    "gw": "3C8A1F2EDE84",
    "on": True,
    "mode": 1,
    "waterTemp": 49.0,
    "comfortTemp": 54.0,
    "reducedTemp": 16.0,
    "procReqTemp": 54.0,
    "opMode": 1,
    "holidayUntil": None,
    "boostOn": False,
    "hpState": 2,
}


def _device() -> AristonNuosSplitDevice:
    """Instantiate without the abstract machinery; only api+gw are used."""
    cls = AristonNuosSplitDevice
    original = cls.__abstractmethods__
    cls.__abstractmethods__ = frozenset()
    try:
        device = cls.__new__(cls)
    finally:
        cls.__abstractmethods__ = original
    device.api = AristonAPI("user", "pass")
    device.gw = "3C8A1F2EDE84"
    device.data = {}
    return device


class NuosPlantModeTests(unittest.TestCase):
    """Manual / Program is written as viewModel.plantMode through R2."""

    def test_enum_values(self) -> None:
        self.assertEqual(NuosSplitPlantMode.MANUAL.value, 1)
        self.assertEqual(NuosSplitPlantMode.PROGRAM.value, 2)

    def test_payload_plant_mode_keeps_op_mode(self) -> None:
        payload = AristonAPI._build_nuos_r2_payload(
            PLANT, plant_mode=NuosSplitPlantMode.PROGRAM.value
        )
        self.assertEqual(payload["viewModel"]["plantMode"], 2)
        self.assertEqual(payload["viewModel"]["opMode"], 1)  # unchanged
        self.assertEqual(payload["plantData"]["mode"], 1)  # echoed back

    def test_payload_op_mode_keeps_plant_mode(self) -> None:
        payload = AristonAPI._build_nuos_r2_payload(
            PLANT, NuosSplitOperativeMode.GREEN.value
        )
        self.assertEqual(payload["viewModel"]["opMode"], 0)
        self.assertEqual(payload["viewModel"]["plantMode"], 1)

    def test_getters(self) -> None:
        device = _device()
        self.assertIsNone(device.water_heater_plant_mode_text)
        device.data = dict(PLANT, mode=2)
        self.assertEqual(device.water_heater_plant_mode_value, 2)
        self.assertEqual(device.water_heater_plant_mode_text, "PROGRAM")
        self.assertEqual(device.water_heater_plant_mode_texts, ["MANUAL", "PROGRAM"])
        device.data["mode"] = 99
        self.assertIsNone(device.water_heater_plant_mode_text)

    def test_sync_setter(self) -> None:
        device = _device()
        device.api.set_nuos_plant_mode_via_r2 = MagicMock()  # type: ignore[method-assign]
        device.set_water_heater_plant_mode("PROGRAM")
        device.api.set_nuos_plant_mode_via_r2.assert_called_once_with(
            device.gw, NuosSplitPlantMode.PROGRAM
        )
        self.assertEqual(device.data["mode"], 2)

    def test_async_setter(self) -> None:
        device = _device()
        device.api.async_set_nuos_plant_mode_via_r2 = AsyncMock()  # type: ignore[method-assign]
        asyncio.run(device.async_set_water_heater_plant_mode("MANUAL"))
        device.api.async_set_nuos_plant_mode_via_r2.assert_awaited_once_with(
            device.gw, NuosSplitPlantMode.MANUAL
        )
        self.assertEqual(device.data["mode"], 1)

    def test_api_async_flow_posts_plant_mode(self) -> None:
        api = AristonAPI("user", "pass")
        api._async_r2_login = AsyncMock()  # type: ignore[method-assign]
        api._async_r2_get_slp_plant_data = AsyncMock(return_value=PLANT)  # type: ignore[method-assign]
        api._async_r2_post_set_data = AsyncMock()  # type: ignore[method-assign]
        asyncio.run(
            api.async_set_nuos_plant_mode_via_r2("gw-1", NuosSplitPlantMode.PROGRAM)
        )
        api._async_r2_login.assert_awaited_once()
        gw, payload = api._async_r2_post_set_data.await_args.args
        self.assertEqual(gw, "gw-1")
        self.assertEqual(payload["viewModel"]["plantMode"], 2)
        self.assertEqual(payload["viewModel"]["opMode"], 1)

    def test_api_sync_flow_posts_plant_mode(self) -> None:
        api = AristonAPI("user", "pass")
        api._r2_login = MagicMock()  # type: ignore[method-assign]
        api._r2_get_slp_plant_data = MagicMock(return_value=PLANT)  # type: ignore[method-assign]
        api._r2_post_set_data = MagicMock()  # type: ignore[method-assign]
        api.set_nuos_plant_mode_via_r2("gw-1", NuosSplitPlantMode.PROGRAM)
        api._r2_post_set_data.assert_called_once()
        gw, payload = api._r2_post_set_data.call_args.args
        self.assertEqual(gw, "gw-1")
        self.assertEqual(payload["viewModel"]["plantMode"], 2)
        self.assertEqual(payload["viewModel"]["opMode"], 1)

    def test_api_sync_retry_after_failed_read(self) -> None:
        """A failed read triggers one fresh login, a reread, then one POST."""
        fresh = dict(PLANT, opMode=3, comfortTemp=60.0)
        api = AristonAPI("user", "pass")
        api._r2_login = MagicMock()  # type: ignore[method-assign]
        api._r2_get_slp_plant_data = MagicMock(  # type: ignore[method-assign]
            side_effect=[ConnectionException("expired"), fresh]
        )
        api._r2_post_set_data = MagicMock()  # type: ignore[method-assign]

        api.set_nuos_plant_mode_via_r2("gw-1", NuosSplitPlantMode.PROGRAM)

        self.assertEqual(api._r2_login.call_count, 2)  # initial + retry
        self.assertEqual(api._r2_get_slp_plant_data.call_count, 2)
        api._r2_post_set_data.assert_called_once()
        gw, payload = api._r2_post_set_data.call_args.args
        self.assertEqual(gw, "gw-1")
        self.assertEqual(payload["viewModel"]["plantMode"], 2)
        self.assertEqual(payload["viewModel"]["opMode"], 3)  # fresh values
        self.assertEqual(payload["viewModel"]["comfortTemp"], 60.0)

    def test_api_async_retry_after_failed_read(self) -> None:
        """Async: a failed read triggers one fresh login, a reread, one POST."""
        fresh = dict(PLANT, opMode=3, comfortTemp=60.0)
        api = AristonAPI("user", "pass")
        api._async_r2_login = AsyncMock()  # type: ignore[method-assign]
        api._async_r2_get_slp_plant_data = AsyncMock(  # type: ignore[method-assign]
            side_effect=[ConnectionException("expired"), fresh]
        )
        api._async_r2_post_set_data = AsyncMock()  # type: ignore[method-assign]

        asyncio.run(
            api.async_set_nuos_plant_mode_via_r2("gw-1", NuosSplitPlantMode.PROGRAM)
        )

        self.assertEqual(api._async_r2_login.await_count, 2)  # initial + retry
        self.assertEqual(api._async_r2_get_slp_plant_data.await_count, 2)
        api._async_r2_post_set_data.assert_awaited_once()
        gw, payload = api._async_r2_post_set_data.await_args.args
        self.assertEqual(gw, "gw-1")
        self.assertEqual(payload["viewModel"]["plantMode"], 2)
        self.assertEqual(payload["viewModel"]["opMode"], 3)  # fresh values
        self.assertEqual(payload["viewModel"]["comfortTemp"], 60.0)


if __name__ == "__main__":
    unittest.main()
