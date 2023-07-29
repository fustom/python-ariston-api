"""BSB device class for Ariston module."""
import logging
from typing import Any, Optional
from .const import BsbZoneMode, BsbZoneProperties, BsbOperativeMode, BsbDeviceProperties, PlantMode, PropertyType
from .device import AristonDevice


_LOGGER = logging.getLogger(__name__)


class AristonBsbDevice(AristonDevice):
    """Class representing a physical device, it's state and properties."""

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return f"Ch{'%2CDhw'}"

    @property
    def water_heater_mode(self) -> type[BsbOperativeMode]:
        """Return the water heater mode class"""
        return BsbOperativeMode

    def update_state(self) -> None:
        """Update the device states from the cloud."""
        self.data = self.api.get_bsb_plant_data(self.gw)

    async def async_update_state(self) -> None:
        """Async update the device states from the cloud."""
        self.data = await self.api.async_get_bsb_plant_data(self.gw)

    def is_plant_in_heat_mode(self) -> bool:
        """Is the plant in a heat mode"""
        return self.get_plant_mode() in [
            PlantMode.WINTER,
            PlantMode.HEATING_ONLY,
        ]

    def get_zone_mode(self, zone: int) -> BsbZoneMode:
        """Get zone mode on value"""
        zone_mode = self._get_zone_property(
            BsbZoneProperties.MODE, PropertyType.VALUE, zone)

        if zone_mode is None:
            return BsbZoneMode.UNDEFINED

        return BsbZoneMode(zone_mode)

    def get_zone_mode_options(self, zone: int) -> list[int]:
        """Get zone mode on options"""
        return self._get_zone_property(
            BsbZoneProperties.MODE, PropertyType.ALLOWED_OPTIONS, zone)

    def get_plant_mode(self) -> PlantMode:
        """Get plant mode on value"""
        # TODO: I don't know how to determine this correctly
        return PlantMode.WINTER

    def get_plant_mode_options(self) -> list[int]:
        """Get plant mode on options"""
        return [PlantMode.SUMMER.value, PlantMode.WINTER.value, PlantMode.OFF.value, PlantMode.HOLIDAY.value]

    def get_plant_mode_opt_texts(self) -> list[str]:
        """Get plant mode on option texts"""
        return [PlantMode.SUMMER, PlantMode.WINTER, PlantMode.OFF, PlantMode.HOLIDAY]

    def get_plant_mode_text(self) -> str:
        """Get plant mode on option texts"""
        self.get_plant_mode()

    @property
    def water_heater_current_temperature(self) -> Optional[float]:
        """Method for getting current water heater temperature."""
        return self.data.get(BsbDeviceProperties.DHW_TEMP, None)

    @property
    def water_heater_minimum_temperature(self) -> float:
        """Method for getting water heater minimum temperature"""
        return self._get_water_heater_property(PropertyType.MIN)

    @property
    def water_heater_target_temperature(self) -> Optional[float]:
        """Method for getting water heater target temperature"""
        return self._get_water_heater_property(PropertyType.VALUE)

    @property
    def water_heater_maximum_temperature(self) -> Optional[float]:
        """Method for getting water heater maximum temperature"""
        return self._get_water_heater_property(PropertyType.MAX)

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
        return [flag.name for flag in self.water_heater_mode]

    @property
    def water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return [flag.value for flag in self.water_heater_mode]

    @property
    def water_heater_mode_value(self) -> Optional[int]:
        """Method for getting water heater mode value"""
        return self.data.get(BsbDeviceProperties.DHW_MODE, dict()).get(PropertyType.VALUE, None)

    def set_water_heater_temperature(self, temperature: float) -> None:
        """Abstract method for set water temperature"""
        raise NotImplementedError

    async def async_set_water_heater_temperature(self, temperature: float) -> None:
        """Abstract method for async set water temperature"""
        raise NotImplementedError

    @property
    def water_heater_temperature_step(self) -> int:
        """Method for getting water heater temperature step"""
        return self._get_water_heater_property(PropertyType.STEP)

    def set_water_heater_operation_mode(self, operation_mode: str) -> None:
        """Abstract method for set water heater operation mode"""
        bsb_operative_mode = BsbOperativeMode[operation_mode]
        self.api.set_bsb_dhw_mode(
            self.gw, bsb_operative_mode, BsbOperativeMode(self.get_water_heater_mode_value()))

        self.data.get(BsbDeviceProperties.DHW_MODE, dict())[
            PropertyType.VALUE] = bsb_operative_mode

    async def async_set_water_heater_operation_mode(self, operation_mode: str) -> None:
        """Abstract method for async set water heater operation mode"""
        bsb_operative_mode = BsbOperativeMode[operation_mode]
        await self.api.async_set_bsb_dhw_mode(self.gw, bsb_operative_mode, BsbOperativeMode(self.get_water_heater_mode_value()))

        self.data.get(BsbDeviceProperties.DHW_MODE, dict())[
            PropertyType.VALUE] = bsb_operative_mode

    def _get_water_heater_property(self, property_name) -> Any:
        """Method for getting water heater property"""
        water_heater_mode = self.get_water_heater_mode_value()
        device_attribute = BsbDeviceProperties.DHW_COMF_TEMP if water_heater_mode == BsbOperativeMode.ON else BsbDeviceProperties.DHW_REDU_TEMP
        return self.data.get(device_attribute, dict()).get(property_name, None)

    def _get_zone_property(self, property_name: BsbZoneProperties, property_value: PropertyType, zone_number: int = 0) -> Any:
        return self.data.get(BsbDeviceProperties.ZONES, dict()).get(str(zone_number), dict()).get(property_name, dict()).get(property_value, None)
