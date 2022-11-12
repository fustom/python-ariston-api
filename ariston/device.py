"""Device class for Ariston module."""
from __future__ import annotations

import datetime as dt
import logging
from abc import ABC, abstractmethod
from typing import Any

from .ariston import (AristonAPI, ConsumptionTimeInterval, ConsumptionType,
                      DeviceAttribute, VelisDeviceAttribute)

_LOGGER = logging.getLogger(__name__)


class AristonDevice(ABC):
    """Class representing a physical device, it's state and properties."""

    def __init__(
        self,
        api: AristonAPI,
        attributes: dict[str, Any],
    ) -> None:
        self.api = api
        self.attributes = attributes

        self.features: dict[str, Any] = dict()
        self.custom_features: dict[str, Any] = dict()
        self.consumptions_settings: dict[str, Any] = dict()
        self.energy_account: dict[str, Any] = dict()
        self.consumptions_sequences: list[dict[str, Any]] = list()
        self.data: dict[str, Any] = dict()
        self.consumption_sequence_last_changed_utc: dt.datetime = (
            dt.datetime.utcfromtimestamp(0).replace(tzinfo=dt.timezone.utc)
        )
        self.gw: str = self.attributes.get(DeviceAttribute.GW, "")

    async def async_get_features(self) -> None:
        """Get device features wrapper"""
        self.features = await self.api.async_get_features_for_device(self.gw)

    async def async_update_state(self) -> None:
        """Update the device states from the cloud"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_temperature_step(self) -> None:
        """Abstract method for get water heater temperature step"""
        raise NotImplementedError

    def get_consumption_sequence_last_changed_utc(self) -> dt.datetime:
        """Get consumption sequence last changed in utc"""
        return self.consumption_sequence_last_changed_utc

    def get_central_heating_total_energy_consumption(self) -> Any:
        """Get central heating total energy consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_total_energy_consumption(self) -> Any:
        """Get domestic hot water total energy consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_central_heating_gas_consumption(self) -> Any:
        """Get central heating gas consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.CENTRAL_HEATING_GAS,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_heating_pump_electricity_consumption(self) -> Any:
        """Get domestic hot water heating pump electricity consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_resistor_electricity_consumption(self) -> Any:
        """Get domestic hot water resistor electricity consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_RESISTOR_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_gas_consumption(self) -> Any:
        """Get domestic hot water gas consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_GAS,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_central_heating_electricity_consumption(self) -> Any:
        """Get central heating electricity consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.CENTRAL_HEATING_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_electricity_consumption(self) -> Any:
        """Get domestic hot water electricity consumption"""
        return self.get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_consumption_sequence_last_value(
        self,
        consumption_type: ConsumptionType,
        time_interval: ConsumptionTimeInterval,
    ) -> Any:
        """Get last value for consumption sequence"""
        if len(self.consumptions_sequences) == 0:
            _LOGGER.exception("Call async_get_consumptions_sequences() first")
            return None
        for sequence in self.consumptions_sequences:
            if sequence["k"] == consumption_type and sequence["p"] == time_interval:
                return sequence["v"][-1]

        return "nan"

    @abstractmethod
    async def async_get_consumptions_sequences(self) -> dict[str, Any]:
        """Get consumption sequence"""
        raise NotImplementedError

    async def async_update_energy(self) -> None:
        """Update the device energy settings from the cloud"""
        old_consumptions_sequences = self.consumptions_sequences
        await self.async_get_consumptions_sequences()

        if (
            self.custom_features.get(ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY.name)
            is None
        ):
            self.set_energy_features()

        if (
            old_consumptions_sequences is not None
            and len(old_consumptions_sequences) > 0
            and old_consumptions_sequences != self.consumptions_sequences
        ):
            self.consumption_sequence_last_changed_utc = dt.datetime.now(
                dt.timezone.utc
            ) - dt.timedelta(hours=1)

    def set_energy_features(self):
        """Set energy features"""
        for consumption_type in ConsumptionType:
            if (consumption_type.name is not None):
                if (
                    self.get_consumption_sequence_last_value(
                        consumption_type,
                        ConsumptionTimeInterval.LAST_DAY,
                    )
                    != "nan"
                ):
                    self.custom_features[consumption_type.name] = True
                else:
                    self.custom_features[consumption_type.name] = False

    def are_device_features_available(
        self, device_features, system_types
    ) -> bool:
        """Checks features availability"""
        if (
            system_types is not None
            and self.attributes.get(DeviceAttribute.SYS) not in system_types
            and self.attributes.get(VelisDeviceAttribute.WHE_TYPE) not in system_types
        ):
            return False

        if device_features is not None:
            for device_feature in device_features:
                if (
                    self.features.get(device_feature) is not True
                    and self.custom_features.get(device_feature) is not True
                ):
                    return False

        return True
