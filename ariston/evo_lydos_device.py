"""Evo and lydos device class for Ariston module."""
from __future__ import annotations

import logging
from typing import Optional

from .velis_device import AristonVelisDevice
from .const import EvoLydosDeviceProperties

_LOGGER = logging.getLogger(__name__)


class AristonEvoLydosDevice(AristonVelisDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def water_heater_current_temperature(self) -> Optional[float]:
        """Get water heater current temperature"""
        return self.data.get(EvoLydosDeviceProperties.TEMP, None)

    @property
    def water_heater_target_temperature(self) -> Optional[float]:
        """Get water heater target temperature"""
        return self.data.get(EvoLydosDeviceProperties.REQ_TEMP, None)

    @property
    def av_shw_value(self) -> Optional[int]:
        """Get average showers value"""
        return self.data.get(EvoLydosDeviceProperties.AV_SHW, None)

    @property
    def is_heating(self) -> Optional[bool]:
        """Get is the water heater heating"""
        return self.data.get(EvoLydosDeviceProperties.HEAT_REQ, None)
