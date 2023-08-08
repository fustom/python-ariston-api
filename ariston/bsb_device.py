"""BSB device class for Ariston module."""
import logging
from typing import Any, Optional

from .const import (
    BsbDeviceProperties,
    BsbOperativeMode,
    BsbZoneMode,
    BsbZoneProperties,
    PropertyType,
)
from .device import AristonDevice

_LOGGER = logging.getLogger(__name__)


class AristonBsbDevice(AristonDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return f"Ch{'%2CDhw'}"

    @property
    def plant_mode_supported(self) -> bool:
        """Returns is plant mode supported"""
        return False

    def update_state(self) -> None:
        """Update the device states from the cloud."""
        self.data = self.api.get_bsb_plant_data(self.gw)

    async def async_update_state(self) -> None:
        """Async update the device states from the cloud."""
        self.data = await self.api.async_get_bsb_plant_data(self.gw)

    @property
    def zone_numbers(self) -> list[int]:
        """Get zone number for device"""
        return [int(zone) for zone in self.zones]

    @property
    def zones(self) -> dict[str, dict[str, Any]]:
        """Get device zones wrapper"""
        return self.data.get(BsbDeviceProperties.ZONES, dict())

    def get_zone(self, zone: int) -> dict[str, Any]:
        """Get device zone"""
        return self.zones.get(str(zone), dict())

    def get_zone_ch_comf_temp(self, zone: int) -> dict[str, Any]:
        """Get device zone central heating comfort temperature"""
        return self.get_zone(zone).get(BsbDeviceProperties.DHW_COMF_TEMP, dict())

    def get_zone_mode(self, zone: int) -> BsbZoneMode:
        """Get zone mode on value"""
        zone_mode = (
            self.get_zone(zone)
            .get(BsbZoneProperties.MODE, dict())
            .get(PropertyType.VALUE, None)
        )

        if zone_mode is None:
            return BsbZoneMode.UNDEFINED

        return BsbZoneMode(zone_mode)

    def get_zone_mode_options(self, zone: int) -> list[int]:
        """Get zone mode on options"""
        return (
            self.get_zone(zone)
            .get(BsbZoneProperties.MODE, dict())
            .get(PropertyType.ALLOWED_OPTIONS, None)
        )

    @property
    def is_plant_in_heat_mode(self) -> bool:
        """Is the plant in a heat mode"""
        return not self.is_plant_in_cool_mode

    @property
    def is_plant_in_cool_mode(self) -> bool:
        """Is the plant in a cool mode"""
        return self.get_zone(self.zone_numbers[0]).get(
            BsbZoneProperties.COOLING_ON, False
        )

    def is_zone_in_manual_mode(self, zone: int) -> bool:
        """Is zone in manual mode"""
        return self.get_zone_mode(zone) in [
            BsbZoneMode.MANUAL,
            BsbZoneMode.MANUAL_NIGHT,
        ]

    def is_zone_in_time_program_mode(self, zone: int) -> bool:
        """Is zone in time program mode"""
        return self.get_zone_mode(zone) in [
            BsbZoneMode.TIME_PROGRAM,
        ]

    def is_zone_mode_options_contains_manual(self, zone: int) -> bool:
        """Is zone mode options contains manual mode"""
        return (
            BsbZoneMode.MANUAL.value or BsbZoneMode.MANUAL_NIGHT.value
        ) in self.get_zone_mode_options(zone)

    def is_zone_mode_options_contains_time_program(self, zone: int) -> bool:
        """Is zone mode options contains time program mode"""
        return BsbZoneMode.TIME_PROGRAM.value in self.get_zone_mode_options(zone)

    def is_zone_mode_options_contains_off(self, zone: int) -> bool:
        """Is zone mode options contains off mode"""
        return BsbZoneMode.OFF.value in self.get_zone_mode_options(zone)

    @property
    def is_flame_on_value(self) -> bool:
        """Get is flame on value"""
        return self.data.get(BsbDeviceProperties.FLAME, False)

    @property
    def water_heater_current_temperature(self) -> Optional[float]:
        """Method for getting current water heater temperature."""
        return self.data.get(BsbDeviceProperties.DHW_TEMP, None)

    @property
    def water_heater_minimum_temperature(self) -> float:
        """Method for getting water heater minimum temperature"""
        return self.data.get(BsbDeviceProperties.DHW_COMF_TEMP, dict()).get(
            PropertyType.MIN, None
        )

    @property
    def water_heater_reduced_minimum_temperature(self) -> Optional[float]:
        """Get water heater reduced temperature"""
        return self.data.get(BsbDeviceProperties.DHW_REDU_TEMP, dict()).get(
            PropertyType.MIN, None
        )

    @property
    def water_heater_target_temperature(self) -> Optional[float]:
        """Method for getting water heater target temperature"""
        return self.data.get(BsbDeviceProperties.DHW_COMF_TEMP, dict()).get(
            PropertyType.VALUE, None
        )

    @property
    def water_heater_reduced_temperature(self) -> Optional[float]:
        """Get water heater reduced temperature"""
        return self.data.get(BsbDeviceProperties.DHW_REDU_TEMP, dict()).get(
            PropertyType.VALUE, None
        )

    @property
    def water_heater_maximum_temperature(self) -> Optional[float]:
        """Method for getting water heater maximum temperature"""
        return self.data.get(BsbDeviceProperties.DHW_COMF_TEMP, dict()).get(
            PropertyType.MAX, None
        )

    @property
    def water_heater_reduced_maximum_temperature(self) -> Optional[float]:
        """Get water heater reduced temperature"""
        return self.data.get(BsbDeviceProperties.DHW_REDU_TEMP, dict()).get(
            PropertyType.MAX, None
        )

    @property
    def water_heater_temperature_step(self) -> int:
        """Method for getting water heater temperature step"""
        return self.data.get(BsbDeviceProperties.DHW_COMF_TEMP, dict()).get(
            PropertyType.STEP, None
        )

    @property
    def water_heater_reduced_temperature_step(self) -> Optional[float]:
        """Get water heater reduced temperature"""
        return self.data.get(BsbDeviceProperties.DHW_REDU_TEMP, dict()).get(
            PropertyType.STEP, None
        )

    @property
    def water_heater_temperature_decimals(self) -> int:
        """Method for getting water heater temperature decimals"""
        return 1

    @property
    def water_heater_temperature_unit(self) -> str:
        """Get water heater temperature unit"""
        return "°C"

    @property
    def water_heater_mode_operation_texts(self) -> list[str]:
        """Get water heater operation mode texts"""
        return [flag.name for flag in BsbOperativeMode]

    @property
    def water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return [flag.value for flag in BsbOperativeMode]

    @property
    def water_heater_mode_value(self) -> Optional[int]:
        """Method for getting water heater mode value"""
        return self.data.get(BsbDeviceProperties.DHW_MODE, dict()).get(
            PropertyType.VALUE, None
        )

    def get_measured_temp_unit(self, zone: int) -> str:
        """Get zone measured temp unit"""
        return "°C"

    def get_measured_temp_decimals(self, zone: int) -> int:
        """Get zone measured temp decimals"""
        return 1

    def get_comfort_temp_min(self, zone: int) -> int:
        """Get zone comfort temp min"""
        return self.get_zone_ch_comf_temp(zone).get(PropertyType.MIN, 7)

    def get_comfort_temp_max(self, zone: int) -> int:
        """Get zone comfort temp max"""
        return self.get_zone_ch_comf_temp(zone).get(PropertyType.MAX, 35)

    def get_comfort_temp_step(self, zone: int) -> int:
        """Get zone comfort temp step"""
        return self.get_zone_ch_comf_temp(zone).get(PropertyType.STEP, 1)

    def get_measured_temp_value(self, zone: int) -> int:
        """Get zone measured temp value"""
        return self.get_zone(zone).get(BsbZoneProperties.ROOM_TEMP, None)

    def get_comfort_temp_value(self, zone: int) -> int:
        """Get zone comfort temp value"""
        return self.get_zone_ch_comf_temp(zone).get(PropertyType.VALUE, None)

    def set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        if len(self.data) == 0:
            self.update_state()
        reduced = self.water_heater_reduced_temperature
        if reduced is None:
            reduced = 0
        self._set_water_heater_temperature(temperature, reduced)

    async def async_set_water_heater_temperature(self, temperature: float):
        """Async set water heater temperature"""
        if len(self.data) == 0:
            await self.async_update_state()
        reduced = self.water_heater_reduced_temperature
        if reduced is None:
            reduced = 0
        await self._async_set_water_heater_temperature(temperature, reduced)

    def set_water_heater_operation_mode(self, operation_mode: str) -> None:
        """Set water heater operation mode"""
        self.api.set_bsb_mode(self.gw, BsbOperativeMode[operation_mode])
        self.data[BsbDeviceProperties.DHW_MODE] = BsbOperativeMode[operation_mode].value

    async def async_set_water_heater_operation_mode(self, operation_mode: str) -> None:
        """Async set water heater operation mode"""
        await self.api.async_set_bsb_mode(self.gw, BsbOperativeMode[operation_mode])
        self.data[BsbDeviceProperties.DHW_MODE] = BsbOperativeMode[operation_mode].value

    def set_water_heater_reduced_temperature(self, temperature: float):
        """Set water heater reduced temperature"""
        if len(self.data) == 0:
            self.update_state()
        current = self.water_heater_current_temperature
        if current is None:
            current = 0
        self._set_water_heater_temperature(current, temperature)

    async def async_set_water_heater_reduced_temperature(self, temperature: float):
        """Async set water heater temperature"""
        if len(self.data) == 0:
            await self.async_update_state()
        current = self.water_heater_current_temperature
        if current is None:
            current = 0
        await self._async_set_water_heater_temperature(current, temperature)

    def _set_water_heater_temperature(self, temperature: float, reduced: float):
        """Set water heater temperature"""
        self.api.set_bsb_temperature(self.gw, temperature, reduced)
        self.data[BsbDeviceProperties.DHW_COMF_TEMP] = temperature
        self.data[BsbDeviceProperties.DHW_REDU_TEMP] = reduced

    async def _async_set_water_heater_temperature(
        self, temperature: float, reduced: float
    ):
        """Async set water heater temperature"""
        await self.api.async_set_bsb_temperature(self.gw, temperature, reduced)
        self.data[BsbDeviceProperties.DHW_COMF_TEMP] = temperature
        self.data[BsbDeviceProperties.DHW_REDU_TEMP] = reduced

    def set_zone_mode(self, zone_mode: BsbZoneMode, zone: int):
        """Set zone mode"""
        self.api.set_bsb_zone_mode(self.gw, zone, zone_mode)

    async def async_set_zone_mode(self, zone_mode: BsbZoneMode, zone: int):
        """Async set zone mode"""
        await self.api.async_set_bsb_zone_mode(self.gw, zone, zone_mode)
