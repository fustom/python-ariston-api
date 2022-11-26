"""Device class for Ariston module."""
from __future__ import annotations

import datetime as dt
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from .ariston_api import AristonAPI
from .const import (
    ConsumptionTimeInterval,
    ConsumptionType,
    DeviceFeatures,
    DeviceAttribute,
    GalevoDeviceAttribute,
    SystemType,
    VelisDeviceAttribute,
    WheType,
)

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
        self.consumptions_sequences: list[dict[str, Any]] = list()
        self.data: dict[str, Any] = dict()
        self.consumption_sequence_last_changed_utc: dt.datetime = (
            dt.datetime.utcfromtimestamp(0).replace(tzinfo=dt.timezone.utc)
        )
        self.gw: str = self.attributes.get(DeviceAttribute.GW, "")

    def get_system_type(self) -> SystemType:
        """Get device system type wrapper"""
        return SystemType(self.attributes.get(DeviceAttribute.SYS, SystemType.UNKNOWN))

    def get_gateway(self) -> str:
        """Get device gateway wrapper"""
        return self.gw

    def get_has_metering(self) -> Optional[bool]:
        """Get device has metering wrapper"""
        return self.features.get(DeviceFeatures.HAS_METERING, None)

    def get_name(self) -> Optional[str]:
        """Get device name wrapper"""
        return self.attributes.get(DeviceAttribute.NAME, None)

    def get_dhw_mode_changeable(self) -> Optional[bool]:
        """Get device domestic hot water mode changeable wrapper"""
        return self.features.get(DeviceFeatures.DHW_MODE_CHANGEABLE, None)

    def get_serial_number(self) -> Optional[str]:
        """Get device serial number wrapper"""
        return self.attributes.get(DeviceAttribute.SN, None)

    def get_firmware_version(self) -> Optional[str]:
        """Get device firmware version wrapper"""
        return self.attributes.get(GalevoDeviceAttribute.FW_VER, None)

    def get_features(self) -> None:
        """Get device features wrapper"""
        self.features = self.api.get_features_for_device(self.gw)

    async def async_get_features(self) -> None:
        """Async get device features wrapper"""
        features = await self.api.async_get_features_for_device(self.gw)
        if features is not None:
            self.features = features

    def get_water_heater_current_mode_text(self) -> str:
        """Get water heater current mode text"""
        mode = self.get_water_heater_mode_value()
        if mode in self.get_water_heater_mode_options():
            index = self.get_water_heater_mode_options().index(mode)
            return self.get_water_heater_mode_operation_texts()[index]
        return "UNKNOWN"

    @abstractmethod
    def update_state(self) -> None:
        """Update the device states from the cloud"""
        raise NotImplementedError

    @abstractmethod
    async def async_update_state(self) -> None:
        """Async update the device states from the cloud"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_current_temperature(self) -> Optional[float]:
        """Abstract method for get water heater current temperature"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_minimum_temperature(self) -> float:
        """Abstract method for get water heater minimum temperature"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_target_temperature(self) -> Optional[float]:
        """Abstract method for get water heater target temperature"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_maximum_temperature(self) -> Optional[float]:
        """Abstract method for get water heater maximum temperature"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_temperature_decimals(self) -> int:
        """Abstract method for get water heater temperature decimals"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_temperature_unit(self) -> str:
        """Abstract method for get water heater temperature unit"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_mode_operation_texts(self) -> list[str]:
        """Abstract method for get water heater operation texts"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_mode_options(self) -> list[int]:
        """Abstract method for get water heater mode options"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_mode_value(self) -> Optional[int]:
        """Abstract method for get water heater mode value"""
        raise NotImplementedError

    @abstractmethod
    def set_water_heater_temperature(self, temperature: float) -> None:
        """Abstract method for set water temperature"""
        raise NotImplementedError

    @abstractmethod
    async def async_set_water_heater_temperature(self, temperature: float) -> None:
        """Abstract method for async set water temperature"""
        raise NotImplementedError

    @abstractmethod
    def get_water_heater_temperature_step(self) -> int:
        """Abstract method for get water heater temperature step"""
        raise NotImplementedError

    def get_consumption_sequence_last_changed_utc(self) -> dt.datetime:
        """Get consumption sequence last changed in utc"""
        return self.consumption_sequence_last_changed_utc

    def get_central_heating_total_energy_consumption(self) -> Any:
        """Get central heating total energy consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.CENTRAL_HEATING_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_total_energy_consumption(self) -> Any:
        """Get domestic hot water total energy consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_TOTAL_ENERGY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_central_heating_gas_consumption(self) -> Any:
        """Get central heating gas consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.CENTRAL_HEATING_GAS,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_heating_pump_electricity_consumption(self) -> Any:
        """Get domestic hot water heating pump electricity consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_resistor_electricity_consumption(self) -> Any:
        """Get domestic hot water resistor electricity consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_RESISTOR_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_gas_consumption(self) -> Any:
        """Get domestic hot water gas consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_GAS,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_central_heating_electricity_consumption(self) -> Any:
        """Get central heating electricity consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.CENTRAL_HEATING_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def get_domestic_hot_water_electricity_consumption(self) -> Any:
        """Get domestic hot water electricity consumption"""
        return self._get_consumption_sequence_last_value(
            ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY,
            ConsumptionTimeInterval.LAST_DAY,
        )

    def _get_consumption_sequence_last_value(
        self,
        consumption_type: ConsumptionType,
        time_interval: ConsumptionTimeInterval,
    ) -> Any:
        """Get last value for consumption sequence"""
        for sequence in self.consumptions_sequences:
            if sequence["k"] == consumption_type and sequence["p"] == time_interval:
                return sequence["v"][-1]

        return None

    @abstractmethod
    def _get_consumptions_sequences(self) -> None:
        """Get consumption sequence"""
        raise NotImplementedError

    @abstractmethod
    async def _async_get_consumptions_sequences(self) -> None:
        """Async get consumption sequence"""
        raise NotImplementedError

    def _update_energy(self, old_consumptions_sequences: list[dict[str, Any]]) -> None:
        """Update the device energy settings"""
        if (
            self.custom_features.get(
                ConsumptionType.DOMESTIC_HOT_WATER_ELECTRICITY.name
            )
            is None
        ):
            self._set_energy_features()

        if (
            old_consumptions_sequences is not None
            and len(old_consumptions_sequences) > 0
            and old_consumptions_sequences != self.consumptions_sequences
        ):
            self.consumption_sequence_last_changed_utc = dt.datetime.now(
                dt.timezone.utc
            ) - dt.timedelta(hours=1)

    def update_energy(self) -> None:
        """Update the device energy settings from the cloud"""
        old_consumptions_sequences = self.consumptions_sequences
        self._get_consumptions_sequences()
        self._update_energy(old_consumptions_sequences)

    async def async_update_energy(self) -> None:
        """Async update the device energy settings from the cloud"""
        old_consumptions_sequences = self.consumptions_sequences
        await self._async_get_consumptions_sequences()
        self._update_energy(old_consumptions_sequences)

    def _set_energy_features(self):
        """Set energy features"""
        for consumption_type in ConsumptionType:
            if consumption_type.name is not None:
                if (
                    self._get_consumption_sequence_last_value(
                        consumption_type,
                        ConsumptionTimeInterval.LAST_DAY,
                    )
                    != None
                ):
                    self.custom_features[consumption_type.name] = True
                else:
                    self.custom_features[consumption_type.name] = False

    def are_device_features_available(
        self,
        device_features: Optional[list[DeviceFeatures]],
        system_types: Optional[list[SystemType | WheType]],
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
                    self.features.get(str(device_feature)) is not True
                    and self.custom_features.get(str(device_feature)) is not True
                ):
                    return False

        return True
