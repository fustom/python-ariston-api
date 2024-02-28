"""Device class for Ariston module."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from .base_device import AristonBaseDevice

_LOGGER = logging.getLogger(__name__)


class AristonDevice(AristonBaseDevice, ABC):
    """Class representing a physical device, it's state and properties."""

    @property
    @abstractmethod
    def water_heater_temperature_decimals(self) -> int:
        """Abstract method for get water heater temperature decimals"""
        raise NotImplementedError

    @property
    @abstractmethod
    def water_heater_temperature_unit(self) -> str:
        """Abstract method for get water heater temperature unit"""
        raise NotImplementedError

    @property
    @abstractmethod
    def water_heater_temperature_step(self) -> int:
        """Abstract method for get water heater temperature step"""
        raise NotImplementedError

    @property
    @abstractmethod
    def water_heater_minimum_temperature(self) -> float:
        """Abstract method for get water heater minimum temperature"""
        raise NotImplementedError

    @property
    @abstractmethod
    def water_heater_target_temperature(self) -> Optional[float]:
        """Abstract method for get water heater target temperature"""
        raise NotImplementedError

    @property
    @abstractmethod
    def water_heater_maximum_temperature(self) -> Optional[float]:
        """Abstract method for get water heater maximum temperature"""
        raise NotImplementedError

    @abstractmethod
    def set_water_heater_temperature(self, temperature: float) -> None:
        """Abstract method for set water temperature"""
        raise NotImplementedError

    @abstractmethod
    async def async_set_water_heater_temperature(self, temperature: float) -> None:
        """Abstract method for async set water temperature"""
        raise NotImplementedError
