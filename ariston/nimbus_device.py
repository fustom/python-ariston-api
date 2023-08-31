"""Nimbus device class for Ariston module."""
from __future__ import annotations

import logging
import asyncio
from typing import Any, Optional

from .galevo_device import AristonGalevoDevice

from .const import (
    ConsumptionType,
    ConsumptionTimeInterval
)

_LOGGER = logging.getLogger(__name__)

class AristonNimbusDevice(AristonGalevoDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def electricity_consumption_for_heating_last_month(self) -> Optional[int]:
        """Get electricity consumption for heating last month"""
        if not self.heating_energy:
            return None
        return self.heating_energy
    
    @property
    def electricity_consumption_for_cooling_last_month(self) -> Optional[int]:
        """Get electricity consumption for cooling last month"""
        if not self.cooling_energy:
            return None
        return self.cooling_energy
    
    def calc_energy_account(self, sequences: dict[str, Any]) -> dict[str, Any]:
        self.heating_energy = 0
        self.cooling_energy = 0
        energy_account = [0] * 61

        for sequence in sequences:
            if sequence['p'] == ConsumptionTimeInterval.LAST_MONTH.value:
                if sequence['k'] == ConsumptionType.CENTRAL_COOLING_TOTAL_ENERGY.value:
                    self.cooling_energy = sum(sequence['v'])
                    energy_account = [cooling+energy for cooling, energy in zip(sequence['v'], energy_account)]
                    
                elif sequence['k'] == ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY.value:
                    self.heating_energy = sum(sequence['v'])
                    energy_account = [heating+energy for heating, energy in zip(sequence['v'], energy_account)]
        
        return {'LastMonth': energy_account }
    
    async def async_calc_energy_account(self, sequences: dict[str, Any]) -> dict[str, Any]:
        self.heating_energy = 0
        self.cooling_energy = 0
        energy_account = [0] * 61

        for sequence in await sequences:
            if sequence['p'] == ConsumptionTimeInterval.LAST_MONTH.value:
                if sequence['k'] == ConsumptionType.CENTRAL_COOLING_TOTAL_ENERGY.value:
                    self.cooling_energy = sum(sequence['v'])
                    energy_account = [cooling+energy for cooling, energy in zip(sequence['v'], energy_account)]
                    
                elif sequence['k'] == ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY.value:
                    self.heating_energy = sum(sequence['v'])
                    energy_account = [heating+energy for heating, energy in zip(sequence['v'], energy_account)]
        
        return {'LastMonth': energy_account }

    def update_energy(self) -> None:
        """Update the device energy settings from the cloud"""
        super().update_energy()

        # These settings only for official clients
        self.consumptions_settings = self.api.get_consumptions_settings(self.gw)
        # Last month consumption in kwh
        self.energy_account = self.calc_energy_account(self.api.get_consumptions_sequences(self.gw, "Ch%2CDhw%2CCooling"))

    async def async_update_energy(self) -> None:
        """Async update the device energy settings from the cloud"""
        (_, self.consumptions_settings, self.energy_account) = await asyncio.gather(
            super().async_update_energy(),
            # These settings only for official clients
            self.api.async_get_consumptions_settings(self.gw),
            # Last month consumption in kwh
            self.async_calc_energy_account(self.api.async_get_consumptions_sequences(self.gw, "Ch%2CDhw%2CCooling"))
        )