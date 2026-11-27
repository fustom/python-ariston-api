"""Unit tests for the Nuos Split heat pump state (hpState)."""

from __future__ import annotations

import unittest

from ariston.const import NuosSplitHpState
from ariston.nuos_split_device import AristonNuosSplitDevice


def _device(data: dict) -> AristonNuosSplitDevice:
    """Instantiate without the abstract machinery; only data is used."""
    cls = AristonNuosSplitDevice
    original = cls.__abstractmethods__
    cls.__abstractmethods__ = frozenset()
    try:
        device = cls.__new__(cls)
    finally:
        cls.__abstractmethods__ = original
    device.data = data
    return device


class NuosHpStateTests(unittest.TestCase):
    """hpState follows the web app enum eSlpHpState."""

    def test_enum_values(self) -> None:
        self.assertEqual(
            {state.name: state.value for state in NuosSplitHpState},
            {
                "LOCKOUT": 0,
                "IDLE": 1,
                "HEATING": 2,
                "ANTILEGIONELLA": 3,
                "ANTIFREEZE": 4,
            },
        )

    def test_known_values(self) -> None:
        for state in NuosSplitHpState:
            device = _device({"hpState": state.value})
            self.assertEqual(device.hp_state_value, state.value)
            self.assertEqual(device.hp_state_text, state.name)

    def test_missing_null_and_unknown(self) -> None:
        for data in ({}, {"hpState": None}, {"hpState": 99}):
            with self.subTest(data=data):
                self.assertIsNone(_device(data).hp_state_text)
        self.assertEqual(_device({"hpState": 99}).hp_state_value, 99)

    def test_texts(self) -> None:
        self.assertEqual(
            _device({}).hp_state_texts,
            ["LOCKOUT", "IDLE", "HEATING", "ANTILEGIONELLA", "ANTIFREEZE"],
        )


if __name__ == "__main__":
    unittest.main()
